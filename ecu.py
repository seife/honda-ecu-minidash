from machine import Pin, UART
from time import sleep, ticks_ms
from micropython import const
import ubinascii


class honda_ecu:
    ECU_WAKEUP_MESSAGE = const(b"\xfe\x04\xff\xff")
    ECU_INIT_MESSAGE = const(b"\x72\x05\x00\xf0\x99")
    ECU_SUCCESS_CHECKSUM = const(0x300)
    last_try = -2000

    def __init__(self, pin_rx, pin_tx, debug_mode=False):
        self.txpin = pin_tx
        self.rxpin = pin_rx
        self.ser = None
        # UART instance is initialized in setup()
        self.debug = debug_mode

    def clear_buf(self, message):
        if self.ser.any():
            if self.debug:
                print(message, end="")
        else:
            return
        while self.ser.any():
            self.ser.read(1)
            if self.debug:
                print(".", end="")
        if self.debug:
            print()

    def dump_buf(self, buf):
        if buf:
            print("dump_buf", ubinascii.hexlify(buf, ":"))

    def setup(self):
        if self.ser:
            self.ser.deinit()
            self.ser = None
        now = ticks_ms()
        if now - self.last_try < 2000:
            return False
        # after the pins have been used for UART, they can no longer be used for
        # plain GPIO stuf unless reinitialized... so do it here.
        self.tx = Pin(self.txpin, mode=Pin.OUT)
        self.rx = Pin(self.rxpin)
        self.last_try = now
        self.tx.low()
        sleep(0.07)
        self.tx.high()
        sleep(0.12)
        self.ser = UART(0, baudrate=10400, tx=self.tx, rx=self.rx)
        self.ser.init(10400, bits=8, parity=None, stop=1)
        self.ser.write(self.ECU_WAKEUP_MESSAGE)
        if self.debug:
            print("wake ", end="")
            self.dump_buf(self.ECU_WAKEUP_MESSAGE)
        self.ser.flush()
        sleep(0.2)
        self.clear_buf("after ECU_WAKEUP_MESSAGE")
        self.ser.write(self.ECU_INIT_MESSAGE)
        if self.debug:
            print("init ", end="")
            self.dump_buf(self.ECU_INIT_MESSAGE)
        self.ser.flush()
        sleep(0.05)

        cksum = 0
        buf = self.ser.read(32)
        if not buf:
            print("ECU_INIT_MESSAGE returned None!")
            return False
        for i in range(0, len(buf)):
            cksum += buf[i]
        if cksum == self.ECU_SUCCESS_CHECKSUM:
            if self.debug:
                print("Successfully opened connection to ECU")
                self.dump_buf(buf)
            return True
        if self.debug:
            print("Failed to open connection to ECU, trying again in 2s")
            print("got", len(buf), "bytes, chksum:", cksum, "correct:", self.ECU_SUCCESS_CHECKSUM)
            self.dump_buf(buf)
        return False

    def calc_chksum(self, data):
        cksum = 0
        for i in range(0, len(data)):
            cksum -= data[i]
        return cksum % 256

    def get_data_table(self, table, tlen):
        data = b"\x72\x05\x71" + bytes([table])
        chk = self.calc_chksum(data)
        data += bytes([chk])
        self.clear_buf("get_data_table")
        self.ser.write(data)
        self.ser.flush()
        dummy = self.ser.read(len(data))
        if not dummy:
            return None
        if len(data) != len(dummy):
            print("get_data_table: did not read as much as I have sent!")
            print(len(data), len(dummy))
        now = ticks_ms()
        while not self.ser.any():
            sleep(0.001)
            if ticks_ms() - now > 150:
                print("get_data_table TIMEOUT!")
                return None
        response = self.ser.read(tlen + 5)
        rl = 0
        if response:
            chk = self.calc_chksum(response)
            rl = len(response)
        if not response or chk != 0:
            print(f"Data table 0x{table:02x} chksum difference: {chk} bytes received: {rl}")
            self.dump_buf(response)
            return None
        if rl != tlen + 5:
            print(f"Data table 0x{table:02x} wrong len {rl} expected {tlen + 4}")
        # print(f"data table 0x{table:x} ", end="")
        # self.dump_buf(response)
        return response[4:]
