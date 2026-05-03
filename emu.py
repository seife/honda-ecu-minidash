# import ubinascii
import random
import time
import os


# dummy Pin class
class Pin:
    OUT = 0
    IN = 1

    def __init__(self, pin, mode=IN):
        pass

    def low(self):
        pass

    def high(self):
        pass

    def value(self, arg1):
        pass


# emulates dummy UART class
class UART:
    rpm = 0
    ect = 0
    kmh = 0
    inj = 0

    def __init__(self, num=0, baudrate=0, tx=Pin(0), rx=Pin(1)):
        self.message = ""
        random.seed()
        pass

    def init(self, baud, bits, parity, stop):
        self.message = ""
        pass

    def write(self, message):
        init = b"\x72\x05\x00\xf0\x99"
        table_d1 = b"\x72\x05\x71\xd1\x47"  # include chksum
        table_11 = b"\x72\x05\x71\x11\x07"
        resp_d1 = b"\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00"
        resp_11 = b"\x00\x00\x00\x00\x00\x00\x18\x00\x99\x40\x99\x3f\x99\x63\xff\xff\x78\x00\x00\x00\x80\x63\x18\x51"
        if message == init:
            self.message = b"\x02\x04\x00\xfa\xff\xff\x02"  # FFFF02 made up to match chksum
            return
        elif message == table_d1:
            self.message = message + resp_d1 + bytes([self.__chksum(resp_d1)])
            # print("table_d1", ubinascii.hexlify(self.message, ":"))
        elif message == table_11:
            resp = bytearray(resp_11)
            self.rpm += random.randint(-100, 100)
            self.rpm = 1800 if self.rpm < 1800 else self.rpm
            self.rpm = 6000 if self.rpm > 6000 else self.rpm
            self.ect += random.randint(-10, 10)
            self.ect = 120 if self.ect > 120 else self.ect
            self.ect = 50 if self.ect < 50 else self.ect
            self.kmh += random.randint(-10, 10)
            self.kmh = 150 if self.kmh > 150 else self.kmh
            self.kmh = 0 if self.kmh < 0 else self.kmh
            if os.getenv("EMU_FUEL"):
                self.inj += random.randint(-500, 500)
                self.inj = 0 if self.inj < 0 else self.inj
                self.inj = 2000 if self.inj > 2000 else self.inj
            resp[4] = (self.rpm >> 8) & 0xFF
            resp[5] = self.rpm & 0xFF
            resp[9] = self.ect + 40
            resp[17] = self.kmh
            resp[18] = (self.inj >> 8) & 0xFF
            resp[19] = self.inj & 0xFF
            resp.append(self.__chksum(resp))
            self.message = message + bytes(resp)
            # print("table_11", ubinascii.hexlify(self.message, ":"))
        else:
            self.message = message
        # print("write", ubinascii.hexlify(message, ":"))

    def read(self, cnt):
        # print("read:", cnt)
        tmp = self.message
        self.message = tmp[cnt:]
        return tmp[:cnt]

    def flush(self):
        pass

    def any(self):
        return len(self.message) > 0

    def deinit(self):
        self.message = ""
        pass

    def __chksum(self, data):
        cksum = 0
        for i in range(0, len(data)):
            cksum -= data[i]
        return cksum % 256


class network:
    STA_IF = 0
    AP_IF = 1

    class WLAN:
        def __init__(self, mode):
            pass

        def active(self, arg1):
            pass

        def connect(self, arg1, arg2):
            pass

        def config(self, essid, password):
            pass

        def ifconfig(self):
            return ("127.0.0.1", "255.0.0.0", "127.0.0.2", "127.0.0.2")

        def isconnected(self):
            return True


def logging_datetime_string():
    dt = time.localtime()
    return "{0:04d}-{1:02d}-{2:02d} {4:02d}:{5:02d}:{6:02d}".format(*dt)
