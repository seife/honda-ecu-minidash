from onewire import OneWire
from ds18x20 import DS18X20
from ssd1306 import SSD1306_I2C

from machine import Pin, I2C
import ecu
import json
import time
import tables

PIN_TX = 0
PIN_RX = 1
PIN_DS = 16   # ds18b20
PIN_SCL = 27  # ssd1306
PIN_SDA = 26

i2c = I2C(id=1, sda=Pin(PIN_SDA), scl=Pin(PIN_SCL))
print("i2c:", i2c.scan())
oled = SSD1306_I2C(128, 32, i2c)

one_wire_bus = Pin(PIN_DS)
sensor_ds = DS18X20(OneWire(one_wire_bus))
ds_dev = None
temp_poll = time.ticks_ms()
temp_last = -99

def get_temp():
    global temp_poll, temp_last, ds_dev
    now = time.ticks_ms()
    if not ds_dev:
        try:
            devices = sensor_ds.scan()
            sensor_ds.convert_temp()
            ds_dev = devices[0]
        except:
            pass
    if now - temp_poll > 1000:
        temp_poll = now
        temp_last = sensor_ds.read_temp(ds_dev)
        sensor_ds.convert_temp()
    return temp_last

def update_oled(temp, rpm, ect, iat, volt, inj):
    oled.fill(0)
    oled.text(f"{temp:5.1f}C {rpm:5d}RPM", 0, 0)
    oled.text(f"{volt:4.1f}V {inj}INJ", 0, 12)
    oled.text(f"{ect} ECT {iat} IAT", 0, 24)
    oled.show()

def load_stats():
    try:
        with open("/data.json") as d:
            return json.load(d)
    except:
        return {}

def save_stats(fuel):
    save = {"fuel": fuel}
    with open("/data.json", "w") as d:
        json.dump(save, d)

def main():
    bike = ecu.honda_ecu(pin_tx=PIN_TX, pin_rx=PIN_RX, debug_mode=True)
    ecu_connected = False
    comm_err = 0
    fuel = 0
    lastscan = -1
    stats = load_stats()
    lastsave = time.ticks_ms()
    if "fuel" in stats:
        fuel = stats["fuel"]
    while True:
        temp = get_temp()
        # print("Temperature:", temp)
        time.sleep_ms(250 - time.ticks_ms() % 250)
        if not ecu_connected or comm_err > 3:
            ecu_connected = bike.setup()
            lastscan = -1
            if ecu_connected:
                comm_err = 0

        if not ecu_connected:
            # print("not connected...")
            update_oled(temp, 0, -99, -99, 0.0, 9999)
            continue

        data_d1 = bike.get_data_table(0xd1, tables.tD1.tlen)
        if not data_d1:
            print("not data_d1!")
            comm_err += 1
            continue
        data_11 = bike.get_data_table(0x11, tables.t11.tlen)
        if not data_11:
            print("not data_11!")
            comm_err += 1
            continue
        if comm_err > 0:
            print("comm_err", comm_err)
            comm_err -= 1
        t_d1 = tables.tD1(data_d1)
        t_11 = tables.t11(data_11)
        rpm = t_11.rpm
        ect = t_11.ect_degc
        iat = t_11.iat_degc
        bat = t_11.bat_volt
        kmh = t_11.km_h
        inj = t_11.inj
        if lastscan > 0:
            now = time.ticks_ms()
            scantime = now - lastscan
            lastscan = now
            fuel += rpm * inj * scantime / 1000
            if lastsave - now > 60000:
                save_stats(fuel)
                lastsave = now
        print(f"rpm {rpm} ect {ect} iat {iat} bat {bat} kmh {kmh} inj {inj}")
        print(t_d1.sw1, t_d1.eng, fuel)
        update_oled(temp, t_11.rpm, t_11.ect_degc, t_11.iat_degc, t_11.bat_volt, t_11.inj)

if __name__ == "__main__":
    main()
