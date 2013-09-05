#!/usr/bin/env python

import obd_io
import serial
import platform
import obd_sensors
from PIL import Image,ImageDraw,ImageFont
import ImageOps
import nokiaSPI
import time
import os
import sqlite3
import wiringpi
from obd_utils import scanSerial
INPUT=0
OUTPUT=1

class OBD_Capture():
	def __init__(self):
		self.port = None
		wiringpi.wiringPiSetup()
		wiringpi.pinMode(5,INPUT)  #Physical pin 18, BCM GPIO 24
		wiringpi.pinMode(6,OUTPUT)	#Physical pin 22, BCM GPIO 25
		wiringpi.digitalWrite(6,1)  #Set output high 

	def connect(self):
		portnames = scanSerial()
		print portnames
		for port in portnames:
			self.port = obd_io.OBDPort(port, None, 2, 2)
			if(self.port.State == 0):
				self.port.close()
				self.port = None
			else:
				break

		if(self.port):
			print "Connected to "+self.port.port.name

	def is_connected(self):
		return self.port

	def nokiprint(self,cShortTerm,cLongTerm,cLongTermMinutes):
		cShortTerm = cShortTerm[:4]
		cLongTerm = cLongTerm[:4]
		noki.cls()
		im = Image.new('1', (84,48))
		draw = ImageDraw.Draw(im)
		draw.text((0,0),cShortTerm, font=font, fill=1)
		draw.text((0,24),cLongTerm, font=font, fill=1)
		draw.text((54,7),"3 s", font=fontsmall, fill=1)
		draw.text((54,31),cLongTermMinutes + " m", font=fontsmall, fill=1)
		# Copy it to the display
		noki.show_image(im)
		
	def ComputeFuelConsumption(self):
		nStartSec = time.time() - 20
		
		try:
			cLimit = " and time_read > " + str(nStartSec) + " order by time_read desc limit 6)"
			self.cursor.execute('''SELECT  avg((3600 * maf)/(9069.90 * speed)) FROM (select maf,speed from SensorReadings where speed > "0" and maf > "0" and rpm != "NODATA" ''' + cLimit)
			data = self.cursor.fetchone()
		except sqlite3.OperationalError,msg:
			return msg
		
		if (len(data) > 0):
			nAvgFuelConsumption = data[0]
						
			try:
				nAvgFuelConsumption = float(nAvgFuelConsumption)
				return "{:5.2f}".format(nAvgFuelConsumption).lstrip()
			except TypeError:
				return "No data"	
				 	
		else:
			return "No data"
		
	def is_number(self,DataToTest):
		try:
			float(DataToTest)
			return True
		except ValueError:
			return False

	def has_ShutdownButtonBeenPressed(self):
		if (wiringpi.digitalRead(5) == 1):
			self.cursor.close()
			self.conn.close()
			time.sleep(0.5)
			os.system("sudo poweroff")		
		
	def capture_data(self):
		#Creating new database
		for kounter in range(10000):
			cKounter = "{0:05d}".format(kounter)
			cNewDatabase = "obdii" + cKounter + ".db"
			if not (os.path.exists(cNewDatabase)):
				break

		self.conn = sqlite3.connect(cNewDatabase)
		self.cursor = self.conn.cursor()
			
		#Find supported sensors - by getting PIDs from OBD
		# its a string of binary 01010101010101 
		# 1 means the sensor is supported
		self.supp = self.port.sensor(0)[1]
		self.supportedSensorList = []
		self.unsupportedSensorList = []
		
		
		# loop through PIDs binary
		for i in range(0, len(self.supp)):
			if self.supp[i] == "1":
				# store index of sensor and sensor object
				self.supportedSensorList.append([i+1, obd_sensors.SENSORS[i+1]])
			else:
				self.unsupportedSensorList.append([i+1, obd_sensors.SENSORS[i+1]])
		
		sqlCreateTable = "CREATE TABLE SensorReadings (time_read real, "
		sqlInsertTemplate = "INSERT INTO SensorReadings(time_read, "
		
		for supportedSensor in self.supportedSensorList:
			sqlCreateTable += str(supportedSensor[1].shortname)  + " text,"	
			sqlInsertTemplate += str(supportedSensor[1].shortname)  + ","
			
		sqlCreateTable = sqlCreateTable[:sqlCreateTable.rfind(",")] + ")"
		
		try:
			self.cursor.execute(sqlCreateTable)
			self.conn.commit()
			self.cursor.execute('''CREATE INDEX time_read_index on SensorReadings(time_read)''')
			cMessage = "Database " + cNewDatabase + " created..."
		except sqlite3.OperationalError,msg:
			cMessage = msg
			
		noki.cls()
		noki.text(cMessage,wrap=True)
		
		sqlInsertTemplate = sqlInsertTemplate[:sqlInsertTemplate.rfind(",")] + ") VALUES ("
		
		time.sleep(3)

		if(self.port is None):
			return None
		
		#Loop until Ctrl C is pressed        
		try:
			nRunningTotalFuelConsumption = 0
			nStartTime = time.time()
			x = 0
			while True:
				self.has_ShutdownButtonBeenPressed()
				current_time = time.time()
				sqlInsert = sqlInsertTemplate + '"' + str(current_time) + '",'
				results = {}
				for supportedSensor in self.supportedSensorList:
					sensorIndex = supportedSensor[0]
					(name, value, unit) = self.port.sensor(sensorIndex)
					sqlInsert += '"' + str(value) + '",'	
				
				
				sqlInsert = sqlInsert[:sqlInsert.rfind(",")] + ")"

				try:
					self.cursor.execute(sqlInsert)
					self.conn.commit()
				except sqlite3.OperationalError,msg:
					noki.cls()
					noki.text(msg,wrap=True)	
					continue
					
				cFuelConsumption = self.ComputeFuelConsumption()
				if (cFuelConsumption != "No data"):
					x += 1
				if (x > 0):
					if (self.is_number(cFuelConsumption)):
						nRunningTotalFuelConsumption += float(cFuelConsumption)
					nTripAverage = nRunningTotalFuelConsumption/x
					cTripAverage = "{:5.2f}".format(nTripAverage).lstrip()
				else:
					cTripAverage = "Nodata"
				
				cDurationInMinutes = "{:3.0f}".format((current_time - nStartTime)/60).lstrip()
				self.nokiprint(cFuelConsumption,cTripAverage,cDurationInMinutes)
				

		except KeyboardInterrupt:
			self.port.close()
			print("stopped")
			
if __name__ == "__main__":
	font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",26)
	fontsmall = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", 16)
	# New b-w image
	im = Image.new('1', (84,48))
	noki = nokiaSPI.NokiaSPI(brightness=268)              # create display device
	noki.cls()
	noki.text("Initializing..",wrap=True)


	o = OBD_Capture()
	o.connect()
	time.sleep(3)
	if not o.is_connected():
		print "Not connected"
		noki.cls()
		noki.text("Error: Not connected to OBDII...",wrap=True)
		time.sleep(10)
		noki.set_brightness(0)
		noki.cls()
		exit()
	else:
		o.capture_data()
