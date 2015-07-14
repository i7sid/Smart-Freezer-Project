import re
import time
import os
import datetime

import RPi.GPIO as GPIO

class TempController(object):
    # Configuration of temeprature controller

    tempOn = -16.0 # temperature where to switch on cooling unit
    tempOff = -18.0 # temperature limit where to switch of cooling unit

    #tempOutFile = "/sys/bus/w1/devices/28-000001357199/w1_slave" # w1_slave file of sensor in /sys/bus/w1/devices
    #tempInFile = "/sys/bus/w1/devices/10-000802b53a6e/w1_slave" # w1_slave file of sensor
    tempOutFile = "/sys/devices/w1_bus_master1/28-000001357199/w1_slave"
    tempInFile = "/sys/devices/w1_bus_master1/28-000001357199/w1_slave"

    waitTime = 180 # wait time in seconds where the temperature has to be
                   # higher than tempOn before switching on the cooling unit

    enableWatchdog = False # Enable bcm2708 watchdog module

    gpioPinRelais = 17

    ######## Configuration end ############

    tempOut = None # temperature outside of freezer
    tempOutLastUpdate = None # timestamp of last (successful) update
    tempIn = None # temeprature inside of freezer
    tempInLastUpdate = None # timestamp of last (successful) update

    tempWaitTimePeriod = None

    watchdogFileHandle = None

    ctrlMode = None

    MODE_TEMPERATURE_CTRL = 'temp'
    MODE_FAILSAFE = 'fail'

    lastSwitchAction = None
    lastSwitchStatus = None # on / off

    def run(self):
        if self.enableWatchdog:
            os.system('modprobe bcm2708_wdog heartbeat=15 nowayout=1')
            self.watchdogFileHandle = open("/dev/watchdog", "w")

        # setup gpio pin for relais
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpioPinRelais, GPIO.OUT)

        while 1:
            if self.enableWatchdog:
                self.watchdogFileHandle.write("a")
            self.work()
            time.sleep(5)

    def temperatureValid(self, sensor):
        if sensor == 'out':
            if self.tempOutLastUpdate == None:
                return False
            diff = time.time() - self.tempOutLastUpdate
        else:
            if self.tempInLastUpdate == None:
                return False
            diff = time.time() - self.tempInLastUpdate
        if diff > 180:
            return False
        return True

    def writeTemperature(self, sensor):
        if sensor == 'out':
            self.writeFile("/run/shm/temp.outside", str(self.tempOut))
        else:
            self.writeFile("/run/shm/temp.inside", str(self.tempIn))

    def writeFile(self, fileName, fileContent):
        outFile = open(fileName, "w")
        outFile.truncate()
        outFile.write(fileContent)
        outFile.close()

    def work(self):
	self.updateTemperatures()
        self.writeTemperature('in')
        self.writeTemperature('out')

        tempWish = self.readFileIntoString("/run/shm/temp.wish")
        if tempWish:
            tempWish = float(tempWish)
            if tempWish < 10 and tempWish > -30:
                self.tempOn = tempWish
                self.tempOff = tempWish - 2

        if self.temperatureValid('in'):
            self.ctrlMode = self.MODE_TEMPERATURE_CTRL
        else:
            self.ctrlMode = self.MODE_FAILSAFE

        if self.ctrlMode == self.MODE_TEMPERATURE_CTRL:
            if self.tempIn > self.tempOn:
                self.switchRelais(True)
            if self.tempIn < self.tempOff:
                self.switchRelais(False)

        if self.ctrlMode == self.MODE_FAILSAFE:
            stat = (datetime.datetime.now().minute / 15) % 2
            if stat:
                self.switchRelais(True)
            else:
                self.switchRelais(False)

        self.writeFile("/run/shm/temp.set", str(self.tempOn))

    def switchRelais(self, on):
        if self.lastSwitchAction:
            if time.time() - self.lastSwitchAction < 180:
                return

        if self.lastSwitchStatus == None:
            if on == True:
                self.lastSwitchStatus = 'off'
            else:
                self.lastSwitchStatus = 'on'

        if on == True and self.lastSwitchStatus == 'off':
            self.lastSwitchAction = time.time()
            self.lastSwitchStatus = 'on'

        if on == False and self.lastSwitchStatus == 'on':
            self.lastSwitchAction = time.time()
            self.lastSwitchStatus = 'off'

        if on == True:
            GPIO.output(self.gpioPinRelais, 1)
            self.writeFile("/run/shm/relais.status", "on")

        if on == False:
            GPIO.output(self.gpioPinRelais, 0)
            self.writeFile("/run/shm/relais.status", "off")

    def updateTemperatures(self):
        tmpTempIn = self.parseTemp1Wire(self.readFileIntoString(self.tempInFile))
        if tmpTempIn:
            self.tempInLastUpdate = time.time()
            self.tempIn = tmpTempIn

        tmpTempOut = self.parseTemp1Wire(self.readFileIntoString(self.tempOutFile))
        if tmpTempOut:
            self.tempOutLastUpdate = time.time()
            self.tempOut = tmpTempOut

    def readFileIntoString(self, file):
        try:
            return open(file).read()
        except IOError:
            pass

    def parseTemp1Wire(self, str):
        if str == None:
            return
        m = re.search('t=([-\d]*)', str)
        if str.find("YES") == -1: # CRC check failed
            return None
        if not m: # Temperature string not found
            return None
        temp = float(m.group(1)) / 1000
        if temp > 80 or temp < -55:
            return None
        return temp

if __name__ == '__main__':
    ctrl = TempController()
    ctrl.run()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
