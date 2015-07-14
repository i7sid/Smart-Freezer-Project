import serial
import struct
import time

def big_to_little(number, size):
    bytes = struct.pack('<I', number)
    ret = []
    for byte in bytes:
        ret.append(ord(byte))
    return ret[0:size]

def little_to_big(str):
    i = 0
    ret = 0
    while i < len(str):
        if i >= 1:
            ret += ord(str[i]) * i * 256
        else:
            ret += ord(str[i])
        i += 1
    return ret

class gt511c3:
    serial = None

    CMD_CMOS_LED = 0x12
    CMD_CHECK_ENROLLED = 0x21
    CMD_ENROLL_START = 0x22
    CMD_ENROLL1 = 0x23
    CMD_ENROLL2 = 0x24
    CMD_ENROLL3 = 0x25
    CMD_IS_PRESS_FINGER = 0x26
    CMD_DELETE_ID = 0x40
    CMD_IDENTIFY = 0x51
    CMD_CAPTURE_FINGER = 0x60

    NACK_INVALID_POS = 0x1003
    NACK_IS_NOT_USED = 0x1004
    NACK_IS_ALREADY_USED = 0x1005
    NACK_DB_IS_FULL = 0x1009
    NACK_FINGER_IS_NOT_PRESSED = 0x1012
    NACK_BAD_FINGER = 0x100c
    NACK_ENROLL_FAILED = 0x100d

    RET_ACK = 0x30
    RET_NACK = 0x31

    QUALITY_LOW = 0
    QUALITY_HIGH = 1

    def __init__(self, serial_port = '/dev/ttyS2'):
        self.serial = serial.Serial(serial_port, 9600)

    def switch_led(self, switch):
        if switch == True:
            self.send_command(self.CMD_CMOS_LED, 1)
        else:
            self.send_command(self.CMD_CMOS_LED, 0)

    def finger_pressed(self):
        ret = self.send_command(self.CMD_IS_PRESS_FINGER)
        if ret[1] > 0:
            return False
        return True

    def delete_fingerprint(self, finger_print_id):
        ret = self.send_command(self.CMD_DELETE_ID, finger_print_id)
        if ret[0] == self.RET_ACK:
            return True
        return False

    def is_enrolled(self, finger_print_id):
        # possible errors: NACK_INVALID_POS, NACK_IS_NOT_USED
        ret = self.send_command(self.CMD_CHECK_ENROLLED, finger_print_id)
        if ret[0] == self.RET_ACK:
            return True
        if ret[1] == self.NACK_IS_NOT_USED:
            return False
        return None

    def get_next_free_fingerprint_id(self):
        for i in range(0, 200):
            if not self.is_enrolled(i):
                return i
        return -1

    def enroll_start(self, finger_print_id):
        ret = self.send_command(self.CMD_ENROLL_START, finger_print_id)
        if ret[0] == self.RET_ACK:
            return True
        return False

    def cmd_enroll(self, num, retry_times = 3):
        ret = self.send_command(self.CMD_ENROLL1 + (num - 1))
        return ret

    # returns true on success, false otherwise
    def capture_fingerprint(self, quality = QUALITY_LOW):
        ret = self.send_command(self.CMD_CAPTURE_FINGER, quality)
        if ret[0] == self.RET_ACK:
            return True
        return False

    def identify(self):
        ret = self.send_command(self.CMD_IDENTIFY)
        if ret[0] == self.RET_ACK:
            return ret[1]
        return -1

    def parse_response(self, bytes):
        parameter = little_to_big(bytes[4:7])
        response = little_to_big(bytes[8:9])

        #print ":".join("{:02x}".format(ord(c)) for c in bytes)

        return [response, parameter]

    def send_command(self, command, parameter = 0):
        bytes = [0x55, 0xAA, 0x01, 0x00]
        bytes = bytes + big_to_little(parameter, 4)
        bytes = bytes + big_to_little(command, 2)

        checksum = 0
        for byte in bytes:
            checksum += byte

        bytes = bytes + big_to_little(checksum, 2)

        self.serial.write(bytes)
        return self.parse_response(self.serial.read(12))
