import json
import os
from phew import dns
from phew.server import logging
import platform
import time
import uasyncio as asyncio
import vfs
import ecu
import tables
import web
import g_vars as G

if platform.platform().startswith("Linux"):
    port = 8888  # without root, no port < 1024 on linux
    # running in "emulated mode", to test the web interface etc.
    from emu import Pin, network, logging_datetime_string

    logging.datetime_string = logging_datetime_string  # patch the function to work without machine.RTC
else:
    port = 80  # web server port
    from machine import Pin
    import network


# import ubinascii
# secrets.py contains
# ssid = "my cool ssid"
# password = "my secret password"
try:
    import secrets

    client_ssid = secrets.ssid
    client_password = secrets.password
except ImportError:
    # no secrets.py...
    client_ssid = ""
    client_password = ""

# constants
global root
root = os.getcwd()
if root.endswith("/"):  # on real board...
    root = root[:-1]
web.root = root  # so that it is available in web.py
STATSDIR = root + "/stats"
PIN_TX = 0
PIN_RX = 1


# ramdisk to write Phew! log file to, taken from micropython doc
class RAMBlockDev:
    def __init__(self, block_size, num_blocks):
        self.block_size = block_size
        self.data = bytearray(block_size * num_blocks)

    def readblocks(self, block_num, buf, offset=0):
        addr = block_num * self.block_size + offset
        for i in range(len(buf)):
            buf[i] = self.data[addr + i]

    def writeblocks(self, block_num, buf, offset=None):
        if offset is None:
            offset = 0
        addr = block_num * self.block_size + offset
        for i in range(len(buf)):
            self.data[addr + i] = buf[i]

    def ioctl(self, op, arg):
        if op == 4:  # get number of blocks
            return len(self.data) // self.block_size
        if op == 5:  # get block size
            return self.block_size
        if op == 6:  # block erase
            return 0


# 6k should be enough, we clip the file at 2k
bdev = RAMBlockDev(512, 12)
vfs.VfsLfs2.mkfs(bdev)
vfs.mount(bdev, root + "/ramdisk")
web.server.logging.log_file = root + "/ramdisk/log.txt"

# end ramdisk

G.state = {"conn": False}


def load_stats():
    try:
        with open(STATSDIR + "/data.json") as d:
            return json.load(d)
    except Exception as e:
        print("load_stats:", e)
        return {}


def save_stats(stats):
    print("save_stats", stats)
    # save = {"fuel": fuel}
    with open(STATSDIR + "/data.json", "w") as d:
        json.dump(stats, d)


def rotate_stats():
    statsfiles = os.listdir(STATSDIR)
    print(f"files in {STATSDIR}:", statsfiles)
    for i in reversed(range(1, 9)):
        name = "data.json." + str(i)
        if name in statsfiles:
            print(f"rename {STATSDIR}/{name} -> {STATSDIR}/data.json.{i + 1}")
            os.rename(f"{STATSDIR}/{name}", f"{STATSDIR}/data.json.{i + 1}")
    print(f"rename {STATSDIR}/data.json -> {STATSDIR}/data.json.1")
    os.rename(f"{STATSDIR}/data.json", f"{STATSDIR}/data.json.1")
    statsfiles = os.listdir(STATSDIR)
    print(f"rotated {STATSDIR}:", statsfiles)


async def mainloop():
    # bike = ecu.honda_ecu(pin_tx=PIN_TX, pin_rx=PIN_RX, debug_mode=True)
    bike = ecu.honda_ecu(pin_tx=PIN_TX, pin_rx=PIN_RX, debug_mode=False)
    ecu_connected = False
    comm_err = 0
    lastscan = -1
    scantime = 0
    lastsave = time.ticks_ms()
    fuel = G.stats.get("fuel", 0)
    div = G.stats.get("div", 4068017877)  # ~ 36408760000/8.95l
    G.stats["div"] = div
    print(f"mainloop: fuel: {fuel} ({type(fuel)}) div: {div} ({type(div)})")
    while True:
        await asyncio.sleep_ms(250 - time.ticks_ms() % 250)
        if not ecu_connected or comm_err > 3:
            ecu_connected = await bike.setup()
            G.state["conn"] = ecu_connected
            lastscan = -1
            if ecu_connected:
                comm_err = 0

        if "update" in G.stats:
            del G.stats["update"]
            try:
                rotate_stats()
            except OSError:
                pass
            save_stats(G.stats)

        if not ecu_connected:
            G.state["fuel"] = fuel
            continue

        data_d1 = await bike.get_data_table(0xD1, tables.tD1.tlen)
        if not data_d1:
            print("not data_d1!")
            comm_err += 1
            continue
        data_11 = await bike.get_data_table(0x11, tables.t11.tlen)
        if not data_11:
            print("not data_11!")
            comm_err += 1
            continue
        if comm_err > 0:
            print("comm_err", comm_err)
            comm_err -= 1
        # print("d1", ubinascii.hexlify(data_d1, ':'))
        # print("11", ubinascii.hexlify(data_11, ':'))
        t_d1 = tables.tD1(data_d1)
        t_11 = tables.t11(data_11)
        rpm = t_11.rpm
        ect = t_11.ect_degc
        iat = t_11.iat_degc
        bat = t_11.bat_volt
        kmh = t_11.km_h
        inj = t_11.inj
        now = time.ticks_ms()
        perhour = 0
        if lastscan > 0:
            scantime = now - lastscan
            add = rpm * inj * scantime / 1000
            fuel += add
            perhour = round(3600000 / scantime * add / div, 1)
            interval = 60000 if kmh > 0 else 5000
            if now - lastsave > interval:
                G.stats["fuel"] = fuel
                save_stats(G.stats)
                lastsave = now
                G.lastsave = now
        lastscan = now
        print(
            f"rpm {rpm} ect {ect} iat {iat} bat {bat} kmh {kmh} inj {inj} sw1 {t_d1.sw1} eng {t_d1.eng} fuel {fuel} ",
            end="",
        )
        print(now, scantime, lastscan, lastsave)
        G.state = {
            "bat": bat,
            "conn": ecu_connected,
            "ect": ect,
            "fuel": fuel,
            "iat": iat,
            "inj": inj,
            "kmh": kmh,
            "per_h": perhour,
            "rpm": rpm,
        }


# blink pattern, depending on connection state
async def wifi_led():
    led = Pin("LED", Pin.OUT)
    led_state = [
        "000000000000",  # nothing connected
        "100010001000",  # AP connected
        "111011101110",  # STA connected
        "111000111000",  # both connected
    ]
    ls = len(led_state[0])
    cnt = 0
    while True:
        wap = G.w_ap.isconnected()
        sta = G.wlan.isconnected()
        idx = wap * 1 + sta * 2
        led.value(int(led_state[idx][cnt]))
        cnt += 1
        cnt %= ls
        await asyncio.sleep_ms(500)


def main():
    G.wlan = network.WLAN(network.STA_IF)
    G.wlan.active(True)
    # print(f"secrets: '{client_ssid}' '{client_password}'")
    G.wlan.connect(client_ssid, client_password)
    G.w_ap = network.WLAN(network.AP_IF)
    G.w_ap.config(essid="pico", password="12345678")
    G.w_ap.active(True)
    print("wlan", G.wlan.ifconfig())
    print("w_ap", G.w_ap.ifconfig())
    x = G.w_ap.ifconfig()
    try:
        dns.run_catchall(x[0])
    except OSError as e:  # on a linux host, port 53 is not available to non-root
        print(f"no catchall dns (not running as root probably, which is OK)... {e}")
    try:
        print(f"stats dir: {STATSDIR}")
        os.mkdir(STATSDIR)
    except OSError as e:
        print(f"mkdir stats: {e}")
        pass
    G.stats = load_stats()
    # Phew! internals: there is already a "run all tasks" routine...
    loop = web.server.loop
    loop.create_task(mainloop())
    loop.create_task(wifi_led())
    # adds the Phew! task, runs all...
    web.server.run(port=port)
    # loop.run_forever()


if __name__ == "__main__":
    main()
