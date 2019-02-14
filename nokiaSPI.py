#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
######
# GLP - 03-Aug-2013 - Cleaned, expanded, commented
#       Added row and col tracking
#       Added next_row(), next_col(), char_col() and next_char_col()
#       Cleaned up COLUMNS and PER_PIXEL nomenclature
#       Made all data and cmd calls use lcd_data() and lcd_cmd()
#       Added set_contrast()
#       Added wrap logic to text()
#       Added validity assertions to functions that needed them
#       Updated LED brightness test in __main__
# code improvements
#  9/10/12
# WGG - picked up from Raspberry Pi forums and modified with a heavy hand
# -- added spidev support
# -- testing with PIL
# 16-Jan-2013
# -- initial NokiaSPI class

import time
import wiringpi
import spidev
import os
import mmap
import textwrap
from PIL import Image,ImageDraw,ImageFont

# Display size
ROWS = 6 # Times 8 bits = 48 pixels
CHAR_COLUMNS = 14 # Times 6 pixels = 84 pixels
COLUMNS_PER_CHAR = 6 # Eash char is 6 cols wide
COLUMNS = CHAR_COLUMNS * COLUMNS_PER_CHAR
ON = 1
OFF = 0

# GPIO's
'''
DC = 3 # gpio pin 15 = wiringpi no. 3 (BCM 22)
RST = 0 # gpio pin 11 = wiringpi no. 0 (BCM 17)
'''
#The default DC and RST pins for SPI have been changed in RPi 3 and 2.
DC  = 4 # gpio pin 16 = wiringpi np. 4 (BCM 23)
RST = 5 # gpio pin 18 = wiringpi no. 5 (BCM 24)
LED = 1 # gpio pin 12 = wiringpi no. 1 (BCM 18)

# SPI connection
SCE = 10 # gpio pin 24 = wiringpi no. 10 (CE0 BCM 8)
SCLK = 14 # gpio pin 23 = wiringpi no. 14 (SCLK BCM 11)
DIN = 12 # gpio pin 19 = wiringpi no. 12 (MOSI BCM 10)

# For SPI configuration test
BCM2708_PERI_BASE=0x20000000
GPIO_BASE=(BCM2708_PERI_BASE + 0x00200000)
BLOCK_SIZE=4096

CLSBUF=[0]*(ROWS * COLUMNS)

FONT = {
' ': [0x00, 0x00, 0x00, 0x00, 0x00],
'!': [0x00, 0x00, 0x5f, 0x00, 0x00],
'"': [0x00, 0x07, 0x00, 0x07, 0x00],
'#': [0x14, 0x7f, 0x14, 0x7f, 0x14],
'$': [0x24, 0x2a, 0x7f, 0x2a, 0x12],
'%': [0x23, 0x13, 0x08, 0x64, 0x62],
'&': [0x36, 0x49, 0x55, 0x22, 0x50],
"'": [0x00, 0x05, 0x03, 0x00, 0x00],
'(': [0x00, 0x1c, 0x22, 0x41, 0x00],
')': [0x00, 0x41, 0x22, 0x1c, 0x00],
'*': [0x14, 0x08, 0x3e, 0x08, 0x14],
'+': [0x08, 0x08, 0x3e, 0x08, 0x08],
',': [0x00, 0x50, 0x30, 0x00, 0x00],
'-': [0x08, 0x08, 0x08, 0x08, 0x08],
'.': [0x00, 0x60, 0x60, 0x00, 0x00],
'/': [0x20, 0x10, 0x08, 0x04, 0x02],
'0': [0x3e, 0x51, 0x49, 0x45, 0x3e],
'1': [0x00, 0x42, 0x7f, 0x40, 0x00],
'2': [0x42, 0x61, 0x51, 0x49, 0x46],
'3': [0x21, 0x41, 0x45, 0x4b, 0x31],
'4': [0x18, 0x14, 0x12, 0x7f, 0x10],
'5': [0x27, 0x45, 0x45, 0x45, 0x39],
'6': [0x3c, 0x4a, 0x49, 0x49, 0x30],
'7': [0x01, 0x71, 0x09, 0x05, 0x03],
'8': [0x36, 0x49, 0x49, 0x49, 0x36],
'9': [0x06, 0x49, 0x49, 0x29, 0x1e],
':': [0x00, 0x36, 0x36, 0x00, 0x00],
';': [0x00, 0x56, 0x36, 0x00, 0x00],
'<': [0x08, 0x14, 0x22, 0x41, 0x00],
'=': [0x14, 0x14, 0x14, 0x14, 0x14],
'>': [0x00, 0x41, 0x22, 0x14, 0x08],
'?': [0x02, 0x01, 0x51, 0x09, 0x06],
'@': [0x32, 0x49, 0x79, 0x41, 0x3e],
'A': [0x7e, 0x11, 0x11, 0x11, 0x7e],
'B': [0x7f, 0x49, 0x49, 0x49, 0x36],
'C': [0x3e, 0x41, 0x41, 0x41, 0x22],
'D': [0x7f, 0x41, 0x41, 0x22, 0x1c],
'E': [0x7f, 0x49, 0x49, 0x49, 0x41],
'F': [0x7f, 0x09, 0x09, 0x09, 0x01],
'G': [0x3e, 0x41, 0x49, 0x49, 0x7a],
'H': [0x7f, 0x08, 0x08, 0x08, 0x7f],
'I': [0x00, 0x41, 0x7f, 0x41, 0x00],
'J': [0x20, 0x40, 0x41, 0x3f, 0x01],
'K': [0x7f, 0x08, 0x14, 0x22, 0x41],
'L': [0x7f, 0x40, 0x40, 0x40, 0x40],
'M': [0x7f, 0x02, 0x0c, 0x02, 0x7f],
'N': [0x7f, 0x04, 0x08, 0x10, 0x7f],
'O': [0x3e, 0x41, 0x41, 0x41, 0x3e],
'P': [0x7f, 0x09, 0x09, 0x09, 0x06],
'Q': [0x3e, 0x41, 0x51, 0x21, 0x5e],
'R': [0x7f, 0x09, 0x19, 0x29, 0x46],
'S': [0x46, 0x49, 0x49, 0x49, 0x31],
'T': [0x01, 0x01, 0x7f, 0x01, 0x01],
'U': [0x3f, 0x40, 0x40, 0x40, 0x3f],
'V': [0x1f, 0x20, 0x40, 0x20, 0x1f],
'W': [0x3f, 0x40, 0x38, 0x40, 0x3f],
'X': [0x63, 0x14, 0x08, 0x14, 0x63],
'Y': [0x07, 0x08, 0x70, 0x08, 0x07],
'Z': [0x61, 0x51, 0x49, 0x45, 0x43],
'[': [0x00, 0x7f, 0x41, 0x41, 0x00],
'\\': [0x02, 0x04, 0x08, 0x10, 0x20],
']': [0x00, 0x41, 0x41, 0x7f, 0x00],
'^': [0x04, 0x02, 0x01, 0x02, 0x04],
'_': [0x40, 0x40, 0x40, 0x40, 0x40],
'`': [0x00, 0x01, 0x02, 0x04, 0x00],
'a': [0x20, 0x54, 0x54, 0x54, 0x78],
'b': [0x7f, 0x48, 0x44, 0x44, 0x38],
'c': [0x38, 0x44, 0x44, 0x44, 0x20],
'd': [0x38, 0x44, 0x44, 0x48, 0x7f],
'e': [0x38, 0x54, 0x54, 0x54, 0x18],
'f': [0x08, 0x7e, 0x09, 0x01, 0x02],
'g': [0x0c, 0x52, 0x52, 0x52, 0x3e],
'h': [0x7f, 0x08, 0x04, 0x04, 0x78],
'i': [0x00, 0x44, 0x7d, 0x40, 0x00],
'j': [0x20, 0x40, 0x44, 0x3d, 0x00],
'k': [0x7f, 0x10, 0x28, 0x44, 0x00],
'l': [0x00, 0x41, 0x7f, 0x40, 0x00],
'm': [0x7c, 0x04, 0x18, 0x04, 0x78],
'n': [0x7c, 0x08, 0x04, 0x04, 0x78],
'o': [0x38, 0x44, 0x44, 0x44, 0x38],
'p': [0x7c, 0x14, 0x14, 0x14, 0x08],
'q': [0x08, 0x14, 0x14, 0x18, 0x7c],
'r': [0x7c, 0x08, 0x04, 0x04, 0x08],
's': [0x48, 0x54, 0x54, 0x54, 0x20],
't': [0x04, 0x3f, 0x44, 0x40, 0x20],
'u': [0x3c, 0x40, 0x40, 0x20, 0x7c],
'v': [0x1c, 0x20, 0x40, 0x20, 0x1c],
'w': [0x3c, 0x40, 0x30, 0x40, 0x3c],
'x': [0x44, 0x28, 0x10, 0x28, 0x44],
'y': [0x0c, 0x50, 0x50, 0x50, 0x3c],
'z': [0x44, 0x64, 0x54, 0x4c, 0x44],
'{': [0x00, 0x08, 0x36, 0x41, 0x00],
'|': [0x00, 0x00, 0x7f, 0x00, 0x00],
'}': [0x00, 0x41, 0x36, 0x08, 0x00],
'~': [0x10, 0x08, 0x08, 0x10, 0x08],
'\x7f': [0x00, 0x7e, 0x42, 0x42, 0x7e],
}

ORIGINAL_CUSTOM = FONT['\x7f']

def bit_reverse(value, width=8):
	#''' Reverse the bits in a byte '''
	result = 0
	for _ in xrange(width):
		result = (result << 1) | (value & 1)
		value >>= 1

	return result

BITREVERSE = map(bit_reverse, xrange(256))

def _strto32bit_(str):
	#   ''' Convert a string to a 32 bit integer '''
	return ((ord(str[3])<<24) + (ord(str[2])<<16) + (ord(str[1])<<8) + ord(str[0]))

def _32bittostr_(val):
	#''' Convert a 32 bit intger to a string '''
	return chr(val&0xff) + chr((val>>8)&0xff) + chr((val>>16)&0xff) + chr((val>>24)&0xff)

def spiConfig():
	#''' Check and update SPI configuration '''
	# Use /dev/mem to gain access to peripheral registers
	mf=os.open("/dev/mem", os.O_RDWR|os.O_SYNC)
	m = mmap.mmap(mf,BLOCK_SIZE, mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE,offset=GPIO_BASE)
	# can close the file after we have mmap
	os.close(mf)
	# Read first two registers (have SPI pin function assignements)
	# GPFSEL0
	m.seek(0)
	reg0=_strto32bit_(m.read(4))
	# GPFSEL1
	m.seek(4)
	reg1=_strto32bit_(m.read(4))
	# print bin(reg0)[2:].zfill(32)[2:]
	# print bin(reg1)[2:].zfill(32)[2:]

	# GPFSEL0 bits --> x[2] SPI0_MISO[3] SPI0_CE0[3] SPI0_CE1[3] x[21]
	# We only use SPI0_CEx depending on setup, but make sure all are set up
	m0 = 0b00111111111000000000000000000000
	s0 = 0b00100100100000000000000000000000
	b0 = reg0 & m0
	if b0 <> s0:
		print "SPI reg0 configuration not correct. Updating."
		reg0 = (reg0 & ~m0) | s0
		m.seek(0)
		m.write(_32bittostr_(reg0))

	# GPFSEL1 bits --> x[26] SPI0_MOSI[3] SPI0_SCLK[3]
	m1 = 0b00000000000000000000000000111111
	s1 = 0b00000000000000000000000000100100
	b1 = reg1 & m1
	if b1 <> s1:
		print "SPI reg1 configuration not correct. Updating."
		reg1 = (reg1 & ~m1) | s1
		m.seek(4)
		m.write(_32bittostr_(reg1))

	# No longer need the mmap
	m.close()

class NokiaSPI:
	def __init__(self, dev=(0,0),speed=5000000, brightness=256, contrast=0xc0):
		self.spi = spidev.SpiDev()
		self.speed = speed
		self.dev = dev
		self.spi.open(self.dev[0],self.dev[1])
		self.spi.max_speed_hz=self.speed
		spiConfig()

		# Set pin directions.
		self.dc = DC
		self.rst = RST
		wiringpi.wiringPiSetup()
		for pin in [self.dc, self.rst]:
			wiringpi.pinMode(pin, 1)

		self.contrast=contrast
		self.brightness=brightness

		# Toggle RST low to reset.
		wiringpi.digitalWrite(self.rst, OFF)
		time.sleep(0.100)
		wiringpi.digitalWrite(self.rst, ON)
		# Initialise LCD
		# 0x21 = Function set (0x20) + Power-down mode (0x04) + Vertical addressing (0x02) + Extended instruction set (0x01)
		# 0x14 = Bias system (0x10) + BS2 (0x04) + BS1 (0x02) + BS0 (0x01)
		# 0xXX = Vop (Operation Voltage) = 0x80 + 7 bits
		# 0x20 = Back to basic instruction set
		# 0x0c = Display Control = 0x08 + 3 bits: D,0,E. 0x04 = Normal mode
		self.lcd_cmd([0x21, 0x14, self.contrast, 0x20, 0x0c])

		self.row = -1
		self.col = -1
		# Clear the screen. This will also initialise self.row and self.col
		self.cls()

		self.ledpin = LED
		if self.ledpin == 1:
			wiringpi.pinMode(self.ledpin, 2)
		else:
			wiringpi.pinMode(self.ledpin, 1)
		self.set_brightness(self.brightness)


	def lcd_cmd(self,value):
		#''' Write a value or list of values to the LCD in COMMAND mode '''
		wiringpi.digitalWrite(self.dc, OFF)
		if type(value) != type([]):
			value = [value]
		self.spi.writebytes(value)


	def lcd_data(self,value):
		#''' Write a value or list of values to the LCD in DATA mode '''
		wiringpi.digitalWrite(self.dc, ON)
		if type(value) != type([]):
			value = [value]
		self.spi.writebytes(value)
		# Calculate new row/col
		# Writing off the end of a row proceeds to the next row
		# Writing off the end of the last row proceeds to the first row
		self.row = (self.row + ((self.col + len(value)) // COLUMNS)) % ROWS
		self.col = (self.col + len(value)) % COLUMNS


	def gotoxy(self, x, y):
		#''' Move the cursor (in memory) to position x, y '''
		assert(0 <= x <= COLUMNS)
		assert(0 <= y <= ROWS)
		# 0x80 = Set X ram address
		# 0x40 = Set Y ram address
		self.lcd_cmd([x+128,y+64])
		self.col = x
		self.row = y


	def cls(self):
		#''' Clear the entire display '''
		self.gotoxy(0, 0)
		self.lcd_data(CLSBUF)
		# Note, we wrote EXACTLY the right number of 0's to return to 0,0


	def fill(self,pattern=0xff):
		fillbuf=[pattern]*(ROWS * COLUMNS)
		self.gotoxy(0, 0)
		self.lcd_data(fillbuf)


	def set_brightness(self, led_value):
		#'''
		#Set the backlight LED brightness. Valid values are 0 <-> 1023
		#When not connected to the PWM port, any value > 0 will turn the LED on full
		#'''
		assert(0 <= led_value <= 1023)

		if self.ledpin == 1:
			wiringpi.pwmWrite(self.ledpin, led_value)
		else:
			if led_value == 0:
				wiringpi.digitalWrite(self.ledpin, OFF)
			else:
				wiringpi.digitalWrite(self.ledpin, ON)
		self.brightness = led_value


	def set_contrast(self, value):
		#''' Set the contrast. Valid values are 0x80 <-> 0xFF '''
		assert(0x80 <= value <= 0xFF)
		self.lcd_cmd([0x21, value, 0x20])
		self.contrast = value


	def load_bitmap(self, filename, reverse=False):
		#''' Load and display a bitmap from a file. reverse displays a negative image '''
		mask = 0xff if reverse else 0x00
		self.gotoxy(0, 0)
		with open(filename, 'rb') as bitmap_file:
			for x in xrange(ROWS):
				for y in xrange(COLUMNS):
					bitmap_file.seek(0x3e + x + (y * 8))
					self.lcd_data(BITREVERSE[ord(bitmap_file.read(1))] ^ mask)


	def show_custom(self, font=FONT):
		#''' Display the custom char from [font] '''
		self.display_char('\x7f', font)


	def define_custom(self, values):
		#''' Overwrite the custom char value in the default font '''
		FONT['\x7f'] = values


	def restore_custom(self):
		#''' Restore the custom char value to it's default in the default font '''
		self.define_custom(ORIGINAL_CUSTOM)


	def alt_custom(self):
		#''' Use an alternate custom char in the default font '''
		self.define_custom([0x00, 0x50, 0x3C, 0x52, 0x44])


	def pi_custom(self):
		#''' Use a raspberry pi icon as the custom char in the default font '''
		self.define_custom([0x19, 0x25, 0x5A, 0x25, 0x19])


	def next_row(self):
		#''' Return the next row, accounting for page wrapping '''
		return (self.row + 1) % ROWS

	def next_col(self):
		#''' Return the next pixel column, accounting for line wrapping '''
		return (self.col + 1) % COLUMNS

	def char_col(self):
		#''' Return the cahracter column (as opposed to self.col which is a pixel column counter) '''
		return self.col / COLUMNS_PER_CHAR

	def next_char_col(self):
		#''' Return the next character column, accounting for line wrapping '''
		return (self.char_col() + 1) % CHAR_COLUMNS


	def display_char(self, char, font=FONT):
		#''' Display a single character. Carriage return clears the remainder of the line and proceeds to the next row '''
		try:
			if char == '\n':
				# Clear the rest of the line. This also puts the cursor at the beginning of the next line.
				self.lcd_data([0] * (COLUMNS - self.col))
			else:
				self.lcd_data(font[char]+[0])

		except KeyError:
			pass # Ignore undefined characters.


	def text(self, string, font=FONT, wrap=True):
		#'''
		#Display a string of text.
		#If wrap is False lines longer than COLUMNS will be truncated and lines beyond ROWS will be discarded
		#'''
		if not wrap:
			for char in string:
				self.display_char(char, font)
		else:
			astring = textwrap.wrap(string,CHAR_COLUMNS)
			for idx,val in enumerate(astring):
				self.gotoxy(0,min(idx,ROWS))
				for char in astring[idx]:
					self.display_char(char, font)
					
	def gotorc(self, r, c):
		#''' Move to character row, column '''
		self.gotoxy(c*6,r)


	def centre_word(self, r, word):
		#''' Display 'word' centered in row 'row' '''
		self.gotorc(r, max(0, (CHAR_COLUMNS - len(word)) // 2))
		self.text(word)


	def show_image(self,im):
		#''' Display an image 'im' '''
		# Rotate and mirror the image
		rim = im.rotate(-90).transpose(Image.FLIP_LEFT_RIGHT)

		# Change display to vertical write mode for graphics
		wiringpi.digitalWrite(DC, OFF)
		self.spi.writebytes([0x22])

		# Start at upper left corner
		self.gotoxy(0, 0)
		# Put on display with reversed bit order
		wiringpi.digitalWrite(DC, ON)
		#self.spi.writebytes( [ BITREVERSE[ord(x)] for x in list(rim.tostring()) ] )
		# "tostring" won't work anymore, use "tobytes"
		self.spi.writebytes( [ BITREVERSE[ord(x)] for x in list(rim.tostring()) ] )

		# Switch back to horizontal write mode for text
		wiringpi.digitalWrite(DC, OFF)
		self.spi.writebytes([0x20])

if __name__ == '__main__':
	# Test all the things!

	start, end = 32, 116
	print 'LCD Display Test: ASCII %d to %d' % (start, end)

	noki = NokiaSPI()

	start_time = time.time()
	noki.cls()
	noki.set_brightness(250)
	if False:
		for i in xrange(start, end):
			noki.display_char(chr(i))

	#finish_time = time.time()
	#print 'Cls, LED on, %d chars, total time = %.3f' % (end - start, finish_time - start_time)

	#time.sleep(1)

	# Test a custom character for 0x7f (supposed to be a bell)
	# . . . - - - - -
	# . . . - - X - -
	# . . . - X X X -
	# . . . - X - X -
	# . . . X - - - X
	# . . . X X X X X
	# . . . - - X X -
	# . . . - - - - -
	noki.define_custom([0x30,0x2c,0x66,0x6c,0x30])

	noki.cls()
	#noki.text("\x7f \x7f \x7f \x7f \x7f \x7f \x7f ")
	#noki.text("    Hello     ")
	#noki.text(" Raspberry Pi")

	#time.sleep(1)

	# Contrast
	noki.cls()
	old_contrast = noki.contrast
	for i in range(0x80,0xFF):
		print "Contrast"
		print i
		noki.set_contrast(i)
		noki.gotorc(2,0)
		noki.text('Contrast:\n%s\n' % hex(i))
		time.sleep(0.1)
	noki.set_contrast(old_contrast)

	#time.sleep(1)
	
	# brightness PWM testing -- off -> 100%
	#noki.cls()
	#for i in range(0,1023,16):
	#	noki.set_brightness(i)
	#	noki.gotorc(2,0)
	#	noki.text("Brightness:\n%s\n" % i)
	#	time.sleep(0.1)
	#noki.set_brightness(1023)
	#noki.gotorc(2,0)
	#noki.text("Brightness:\n%s\n" % 1023)

	#time.sleep(1)

	#noki.set_brightness(768)

	## Generate an image with PIL and put on the display
	## First time through is slow as the fonts are not cached
	##
	start_time = time.time()
	# load an available True Type font
	font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", 26)
	font1 = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", 16)


	# New b-w image
	im = Image.new('1', (84,48))
	# New drawable on image
	draw = ImageDraw.Draw(im)
	# Full screen and half-screen ellipses
	#draw.ellipse((0,0,im.size[0]-1,im.size[1]-1), outline=1)
	#draw.ellipse((im.size[0]/4,im.size[1]/4,im.size[0]/4*3-1,im.size[1]/4*3-1), outline=1)
	# Some simple text for a test (first with TT font, second with default
	draw.text((0,0), "1.11", font=font, fill=1)
	draw.text((0,24), "9.99", font=font, fill=1)
	draw.text((58,7),"3 s", font=font1, fill=1)
	draw.text((58,31),"5 m", font=font1, fill=1)
	# Check what happens when text exceeds width (clipped)
	#draw.text((0,0), "ABCabcDEFdefGHIghi", fill=1)
	# Copy it to the display
	noki.show_image(im)
	# clean up
	del draw
	del im

	finish_time = time.time()
	print 'PIL Drawing, total time = %.3f' % (finish_time - start_time)

	if (os.path.exists("raspi.bmp")):
		start_time = time.time()
		noki.load_bitmap("raspi.bmp")
		finish_time = time.time()
		print 'BMP Load, total time = %.3f' % (finish_time - start_time)

		time.sleep(1)

		start_time = time.time()
		noki.load_bitmap("raspi.bmp", True)	
		finish_time = time.time()
		print 'BMP Load, total time = %.3f' % (finish_time - start_time)

		time.sleep(1)

		start_time = time.time()
		noki.load_bitmap("raspi.bmp")
		finish_time = time.time()
		print 'BMP Load, total time = %.3f' % (finish_time - start_time)

		time.sleep(1)

		start_time = time.time()
		noki.load_bitmap("raspi.bmp", True)
		finish_time = time.time()
		print 'BMP Load, total time = %.3f' % (finish_time - start_time)

		time.sleep(1)

	if os.path.exists("lenna.png"):
		# Let's try some image manipulation
		#start_time = time.time()
		im = Image.open("lenna.png")
		im = im.convert("L")
		im.thumbnail((84,48))
		for t in range(1,255):
			tim = im.point(lambda p: p > t and 255, "1")
			noki.cls()
			noki.show_image(tim)
			noki.gotorc(0,8)
			noki.text("Thresh:")
			noki.gotorc(1,10)
			noki.text("%3d" % t)
			time.sleep(0.01)
			del tim

		#finish_time = time.time()
		#print 'PIL Image, total time = %.3f' % (finish_time - start_time)

		# Let's try some image manipulation
		start_time = time.time()
		im = Image.open("lenna.png")
		#im = im.resize((84,48))
		im.thumbnail((84,48))
		im = im.convert("1")
		noki.cls()
		noki.show_image(im)
		noki.gotorc(0,8)
		noki.text("Dither")

		finish_time = time.time()
		print 'PIL Image, total time = %.3f' % (finish_time - start_time)
