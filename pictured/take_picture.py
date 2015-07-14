#!/usr/bin/python

import os
import shutil
import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BCM)

GPIO.setup(27, GPIO.IN)

def take_picture():
    r = 9

    for i in range(r - 1, 0, -1):
        if not os.path.isfile("/data/pictures/image-" + str(i) + ".jpg"):
            continue
        shutil.move("/data/pictures/image-" + str(i) + ".jpg", "/data/pictures/image-" + str(i + 1) + ".jpg")

    os.system('fswebcam /data/pictures/image-1.jpg')

while True:
    if GPIO.input(27):
        take_picture()

    sleep(1)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
