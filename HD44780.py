#!/usr/bin/python

import RPi.GPIO as GPIO
from time import sleep
import time

from gpiozero import PWMLED
from gpiozero import Button

class HD44780:
	
	  

	def __init__(self, pin_rs=7, pin_e=8, pins_db=[25, 24, 23, 18]):
		self.pin_rs=pin_rs
		self.pin_e=pin_e
		self.pins_db=pins_db
		self.contrast = PWMLED(15,frequency=25)
		self.contrast.on()
		self.contrast.value=.55
		self.Contrastbutton = Button(14)
		self.Contrastbutton.when_pressed = self.ContrastPressed
		
		self.brightness = PWMLED(20,frequency=60)
		self.brightness.on()
		self.brightness.value=.95
		self.Brightnessbutton = Button(21)	
		self.Brightnessbutton.when_pressed = self.BrightnessPressed

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self.pin_e, GPIO.OUT)
		GPIO.setup(self.pin_rs, GPIO.OUT)
		for pin in self.pins_db:
			GPIO.setup(pin, GPIO.OUT)
		self.clear()
		
        
	def ContrastPressed(self):
		nCurrentContrastValue = self.contrast.values.next() + .1
		self.contrast.value = nCurrentContrastValue if nCurrentContrastValue < 1 else .05
		self.clear()
		self.message("Contrast: " + str(self.contrast.values.next()))
		
	def BrightnessPressed(self):
		nCurrentBrightnessValue = self.brightness.values.next() + .1
		self.brightness.value = nCurrentBrightnessValue if nCurrentBrightnessValue < 1.01 else .10
		self.clear()
		self.message("Brightness: " + str(self.brightness.values.next()))	

	def clear(self):
		""" Blank / Reset LCD """

		self.cmd(0x33) # $33 8-bit mode
		self.cmd(0x32) # $32 8-bit mode
		self.cmd(0x28) # $28 8-bit mode
		self.cmd(0x0C) # $0C 8-bit mode
		self.cmd(0x06) # $06 8-bit mode
		self.cmd(0x01) # $01 8-bit mode

	def cmd(self, bits, char_mode=False):
		""" Send command to LCD """

		sleep(0.001)
		bits=bin(bits)[2:].zfill(8)

		GPIO.output(self.pin_rs, char_mode)

		for pin in self.pins_db:
			GPIO.output(pin, False)

		for i in range(4):
			if bits[i] == "1":
				GPIO.output(self.pins_db[::-1][i], True)

		GPIO.output(self.pin_e, True)
		GPIO.output(self.pin_e, False)

		for pin in self.pins_db:
			GPIO.output(pin, False)

		for i in range(4,8):
			if bits[i] == "1":
				GPIO.output(self.pins_db[::-1][i-4], True)


		GPIO.output(self.pin_e, True)
		GPIO.output(self.pin_e, False)

	def message(self, text):
		""" Send string to LCD. Newline wraps to second line"""

		for char in text:
			if char == '\n':
				self.cmd(0xC0) # next line
			else:
				self.cmd(ord(char),True)

if __name__ == '__main__':

	lcd = HD44780()
	while True:
		lcd.clear()
		sleep(.1)
		lcd.message("Database created...\nTesting")
		sleep(1.0)
	GPIO.cleanup()
