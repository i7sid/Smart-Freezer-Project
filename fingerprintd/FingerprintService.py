import sys
import zmq
import json
import time

from gt511c3 import gt511c3
from UserDB import UserDB

sys.path.append( '../displayserver' )
from DisplayClient import DisplayClient

class FingerPrintService:
    dis = None
    gt = None

    state = 1

    state_enroll_timeout = None

    enroll_step = None
    enroll_turn = 1
    enroll_user = None
    enroll_fingerprint_id = None

    STATE_STANDBY = 0 # standby mode (LED off, no fingerprint detection possible)
    STATE_IDENTIFY = 1 # identification mode (LED on)
    STATE_ENROLL = 2 # fingerprint enrolling mode

    # ZeroMQ
    socket = None
    poller = None

    users = None

    booking_queue = {}

    def delete_fingerprint(self, finger_print_id):
        return self.gt.delete_fingerprint(finger_print_id)

    def enroll(self):
        if self.enroll_step == 1:
            self.enroll_fingerprint_id = self.gt.get_next_free_fingerprint_id()
            if self.enroll_fingerprint_id == -1:
                self.dis.send_message_flash("Keine freie Fingerprint ID gefunden...", 20)
                return 'error'

            if not self.gt.enroll_start(self.enroll_fingerprint_id):
                self.dis.send_message_flash("Konnte Fingerabdruckspeicherung nicht starten...", 20)
                return 'error'

            self.enroll_step = 2
            self.enroll_turn = 1

        enroll_ret = None

        for turn in range(self.enroll_turn, 4):
            if self.enroll_step % 2 == 0:
                if self.gt.finger_pressed():
                    self.dis.send_message_flash("Bitte Finger vom Sensor wegnehmen...", 20)
                    return 'continue'
                else:
                    self.enroll_step = self.enroll_step + 1

            if self.enroll_step % 2 == 1:
                if not self.gt.finger_pressed():
                    self.dis.send_message_flash("Bitte Finger auf Sensor legen.. (" + str(turn) + ". Durchgang, ID #" + str(self.enroll_fingerprint_id) + ")", 20)
                    return 'continue'
                else:
                    self.enroll_step = self.enroll_step + 1

            capture = None

            capture = self.gt.capture_fingerprint(self.gt.QUALITY_HIGH)
            if capture:
                enroll_ret = self.gt.cmd_enroll(turn)
                if enroll_ret[0] == self.gt.RET_NACK and enroll_ret[0] < 200:
                    self.dis.send_message_flash("Fingerabdruck schon vorhanden ID #" + str(enroll_ret[1]) + ", breche ab...", 20)
                    return 'error'
                if enroll_ret[0] != self.gt.RET_ACK:
                    self.dis.send_message_flash("Fehler beim Erkennen...", 20)
                    return 'error'
            else:
                self.dis.send_message_flash("Fehler beim Erkennen...", 20)
                return 'error'

            self.enroll_turn = self.enroll_turn + 1

        self.dis.send_message_flash("Fingerabdruck wurde gesepichert... ID #" + str(self.enroll_fingerprint_id), 20)

        self.users.add_fingerprint(self.enroll_user['id'], self.enroll_fingerprint_id)

        return 'success'

    def identify(self):
        if not self.gt.finger_pressed():
            return -1
        #while not self.gt.finger_pressed():
        #    time.sleep(0.1)
        self.gt.capture_fingerprint(self.gt.QUALITY_LOW)
        id = self.gt.identify()
        if id >= 0:
            user = self.users.get_user_by_fingerprint(id)
            self.dis.send_message_flash("Fingerabdruck von Benutzer " + user['name'] + " erkannt...", 20)

            if user['id'] in self.booking_queue:
                del self.booking_queue[user['id']]
                self.dis.send_message_flash([user['name'], "", "Buchung storniert"])
                while self.gt.finger_pressed():
                    pass
            else:
                start = time.time()
                count = 0
                while self.gt.finger_pressed():
                    count = int(time.time() - start)
                    self.dis.send_message_flash([user['name'], str(count) + " Einheiten buchen", "Neuer Kontostand " + str(count + user['bookingcount'])])
                    time.sleep(0.1)

                self.booking_queue[user['id']] = {
                    'count': count,
                    'timestamp': time.time()
                }
                self.dis.send_message_flash([user['name'], str(count) + " Einheiten gebucht", "Zum Stornieren", "Finger auflegen"])
        else:
            self.dis.send_message_flash("Fehler bei der Erkennung...", 20)

    def remove_orphaned_fingerprints(self, finger_prints):
        for i in range(0, 200):
            if self.gt.is_enrolled(i) and i not in finger_prints:
                print "removing orphaned fingerprint id " + str(i)
                self.gt.delete_fingerprint(i)

    def handle_request(self, message):
        if message['command'] == 'get_users':
            self.socket.send(json.dumps(self.users.get_users()))
            return

        if message['command'] == 'remove_fingerprint':
            fingerprint_id = message['fingerprint_id']
            user = self.users.get_user_by_fingerprint(fingerprint_id)
            self.gt.delete_fingerprint(fingerprint_id)
            self.users.remove_fingerprint(user['id'], fingerprint_id)
            self.socket.send(json.dumps('done'))
            return

        if message['command'] == 'get_user':
            self.socket.send(json.dumps(self.users.get_user(message['user_id'])))
            return

        if message['command'] == 'get_bookings':
            self.socket.send(json.dumps(self.users.get_bookings(message['user_id'])))
            return

        if message['command'] == 'change_user':
            user = message['user']
            self.socket.send(json.dumps(self.users.update_user(user['id'], user['name'])))
            return

        if message['command'] == 'remove_user':
            user = self.users.get_user(message['user_id'])
            for fingerprint_id in user['fingerprints']:
                self.gt.delete_fingerprint(fingerprint_id)
                self.users.remove_fingerprint(user['id'], fingerprint_id)
            self.socket.send(json.dumps(self.users.del_user(message['user_id'])))
            return

        if message['command'] == 'enroll':
            self.start_enroll(message['user_id'])
            self.socket.send(json.dumps('done'))
            return

        if message['command'] == 'add_booking':
            self.users.add_booking(message['user_id'], message['count'], message['type'])
            self.socket.send(json.dumps('done'))
            return

        if message['command'] == 'get_state':
            self.socket.send(json.dumps(self.state))
            return

        if message['command'] == 'add_user':
            id = self.users.add_user(message['name'])
            if id:
                self.socket.send(json.dumps(self.users.get_user(id)))
            else:
                self.socket.send(None)
            return

        self.socket.send('no action')

    def start_enroll(self, user_id):
        self.enroll_step = 1
        self.enroll_turn = 1
        self.enroll_user = self.users.get_user(user_id)
        self.state = self.STATE_ENROLL
        self.dis.send_message_flash("Fingerabdruckerkennung gestartet...", 60)

    def loop(self):
        evts = self.poller.poll(500)
        if len(evts) > 0:
            message_encoded = self.socket.recv()
            message = json.loads(message_encoded)

            self.handle_request(message)

        if self.state == self.STATE_IDENTIFY:
            self.identify()

        if self.state == self.STATE_ENROLL:
            ret = self.enroll()
            if ret == 'error' or ret == 'success':
                self.state = self.STATE_IDENTIFY

        for user_id in self.booking_queue.keys():
            booking = self.booking_queue[user_id]
            if booking['timestamp'] < time.time() - 10:
                if booking['count'] > 0:
                    self.users.add_booking(user_id, booking['count'])
                del self.booking_queue[user_id]

    def __init__(self, serial_port):
        self.dis = DisplayClient()
        self.gt = gt511c3(serial_port)
        self.users = UserDB()

        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind("tcp://127.0.0.1:5758")

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        self.dis.send_message_flash("Fingerprint service ready...", 3)

        self.gt.switch_led(1)

if __name__ == '__main__':
    service = FingerPrintService('/dev/ttyS2')
    #service.remove_orphaned_fingerprints([])
    while True:
        service.loop()
