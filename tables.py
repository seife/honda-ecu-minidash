# struct table11 {
# 0  uint8_t rpm_h;
#    uint8_t rpm_l;
#    uint8_t tps_volt;
#    uint8_t tps_perc;
#    uint8_t ect_volt;
# 5  uint8_t ect_degc;
#    uint8_t iat_volt;
#    uint8_t iat_degc;
#    uint8_t map_volt;
#    uint8_t map_kpa;
# 10 uint8_t unk1;
#    uint8_t unk2;
#    uint8_t bat_volt;
#    uint8_t km_h;
#    uint8_t inj_h;
# 15 uint8_t inj_l;
#    uint8_t unk3;
#    uint8_t unk4;
#    uint8_t unk5;
# 19 uint8_t unk6;
# } __attribute__((packed));
class t11:
    tlen = 20

    def __init__(self, buffer):
        if not buffer:
            raise ValueError
        if len(buffer) < self.tlen:
            raise ValueError(f"bufferlen {len(buffer)} < self.tlen {self.tlen}")
        self.buf = buffer
        self.parse()

    def parse(self):
        # fmt: off
        self.rpm      = self.buf[0] * 256 + self.buf[1]
        self.ect_degc = self.buf[5] - 40
        self.iat_degc = self.buf[7] - 40
        self.bat_volt = self.buf[12] / 10
        self.km_h     = self.buf[13]
        self.inj      = self.buf[14] * 256 + self.buf[15]
        # fmt: on


# struct tableD1 {
#    uint8_t sw1;    /* 1 = neutral/clutch; 3 = kickstand, 0 = GO! */
#    uint8_t unk1;
#    uint8_t unk2;
#    uint8_t unk3;
#    uint8_t eng;    /* 1 = engine running */
#    uint8_t unk5;
# };
class tD1:
    tlen = 6

    def __init__(self, buffer):
        if not buffer:
            raise ValueError
        if len(buffer) < self.tlen:
            raise ValueError(f"bufferlen {len(buffer)} < self.tlen {self.tlen}")
        self.buf = buffer
        self.parse()

    def parse(self):
        self.sw1 = self.buf[0]
        self.eng = self.buf[4]
