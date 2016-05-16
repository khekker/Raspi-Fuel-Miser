# Raspi-Fuel-Miser
Keith Hekker, May 16, 2016
LCD Readout of current fuel consumption on OBDII equipped cars (Raspberry Pi Zero)
Operating System: Raspbian Jessie.
Python Version 2.7.
This repository contains a schematic of the wiring required to interconnect the LCD HD44780 to the Raspberry Pi Zero.
It also contains the PCB Fritzing file, which can be turned into Gerber files, ready for sending to a PCB fabricator.
In order for this device to run, you'll need to following Python files installed:
obd_captureHD44780.py,
HD44780.py,obd_io.py,obd_utils.py,obd_sensors.py.
In order for the Python script to automatically start when the Pi boots up, I added this line to /etc/rc.local :
(cd /home/pi/pythonprogs;python obd_capture.py)&
