# Honda ECU fuel consumption monitor in micropython

This is intended to measure the actually consumed amount of fuel (since the last reset), to compensate for the less-than-optimal fuel gauge on the Honda CTX700.

## Theory of operation
To do this, it connects to the ECU and reads values directly from the ECU's data tables and then calculates the amount of fuel used by the engine.
The calculation method is based on code by Ben Gonzales who did a similar project some time ago, documented on https://gonzos.net/projects/ctx-obd/. To calculate the amount of fuel spent, I basically take the raw "inj" number from the data table, multiply this with the "rpm" number and then with the time since the last measure. This gives a unitless number which is added to the "fuel" counter.
To get the amount of fuel in liters, the "fuel" number is divided by a "magic number".
To get the "magic divisor", start with a full tank, then ride some. The code will count the spent fuel. Then when you fill up again (preferrably to the same level you started with), divide the "fuel" number by the liters you filled and get the magic divisor. The code also contains a default.

## Accessing the web interface
Get the Pico into your WiFi, then connect with your browser on port 80 (plain http://your.pico.ip.address/, no https) *or* connect your Phone / PC to the "pico" access point, then go to any hostname, e.g. "http://pi-pico/".

**Attention:** The whole web interface is very basic and experimental right now. Don't consider this "production ready".


# Installing on the Pi Pico W
## Install dependencies
Pimoroni Phew! https://github.com/pimoroni/phew
```
mpremote mip install https://raw.githubusercontent.com/pimoroni/phew/refs/heads/main/
```

## Copy everything onto the board
```
rshell rsync -a . /pyboard/.
```

## Connect to your local WiFi
create a `secrets.py` on the Pi Pico W containing
```
ssid = 'My SSID'
password = 'My Secret Passphrase'
```

The Pico will also create an access point "pico" key "12345678" that you can connect to.

# Wiring the Hardware
To connect to the K-Line interface I used a L9637 chip according to the schematics from https://github.com/aster94/Keyword-Protocol-2000, connecting the TX pin (pin 4) of the L9637 to pin 1 (GP0) of the Pico and the RX pin (pin 1) of the L9637 to pin 2 (GP1) of the Pico.
For the 5V power supply I used a Bauer Electronics DC-DC 8V-32V to 5V/3A step down converter module (which is probably a bit oversized), connected the +5V to pin 39 (VSYS) of the Pico. Do not use pin 40 (VBUS) as this would feed back into the USB port.
Using a good step down converter, preferrably designed for automotive use is probably a good idea to make sure the noisy electrical environment on a motorcycle does not disturb the Pico too much.

# Thanks
* Ben Gonzales https://www.gonzos.net/ for generously sharing the code of his old CTX-OBD project with me, without this, I would not have had any idea how to connect the "fuel" field of the data to actual consumption
* Vincenzo Gibiino (aster94) for the L9637 schematics
* The folks over at the now defunct https://forum.pgmfi.org forum where a wealth of information on Honda ECUs was compiled
