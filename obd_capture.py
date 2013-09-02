#!/usr/bin/env python

import obd_io
import serial
import platform
import obd_sensors
#from datetime import datetime
from PIL import Image,ImageDraw,ImageFont
import ImageOps
import nokiaSPI
import time
import os
import sqlite3
#from datetime import timedelta

from obd_utils import scanSerial

class OBD_Capture():
	def __init__(self):
		self.port = None
		#localtime = time.localtime(time.time())

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
		print cShortTerm
		draw.text((0,0),cShortTerm, font=font, fill=1)
		draw.text((0,24),cLongTerm, font=font, fill=1)
		draw.text((54,7),"3 s", font=fontsmall, fill=1)
		draw.text((54,31),cLongTermMinutes + " m", font=fontsmall, fill=1)
		# Copy it to the display
		noki.show_image(im)
		#noki.next_row()
		
	def ComputeFuelConsumption(self):
		nStartSec = time.time() - 20
		
		try:
			cLimit = " and time_read > " + str(nStartSec) + " order by time_read desc limit 6)"
			#cursor.execute('''SELECT maf,speed from SensorReadings where speed > "0" and maf > "0" and rpm != "NODATA" ''' + cLimit)
			#data = cursor.fetchall()
			self.cursor.execute('''SELECT  avg((3600 * maf)/(9069.90 * speed)) FROM (select maf,speed from SensorReadings where speed > "0" and maf > "0" and rpm != "NODATA" ''' + cLimit)
			data = self.cursor.fetchone()
		except sqlite3.OperationalError,msg:
			return msg
		#print len(data)
		if (len(data) > 0):
			#nFuelConsumption = 0
			#for x in range(0,len(data)):
			#	nFuelConsumption += (3600 * float(data[x][0]))/(9069.90 * float(data[x][1]))
				
			#nAvgFuelConsumption = nFuelConsumption/len(data)
			nAvgFuelConsumption = data[0]
			#print nAvgFuelConsumption
			#print type(nAvgFuelConsumption)
			#print data[x][0],data[x][1],data[x][2]
			
			print type(nAvgFuelConsumption)
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

				
	def capture_data(self):
		#Creating new database
		for kounter in range(10000):
			cKounter = "{0:05d}".format(kounter)
			cNewDatabase = "obdii" + cKounter + ".db"
			#print cNewDatabase
			if not (os.path.exists(cNewDatabase)):
				#print "New database name: " + cNewDatabase
				break

		#global conn
		#global cursor
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
			#print "supported sensor index = " + str(supportedSensor[0]) + " " + str(supportedSensor[1].shortname)
			sqlCreateTable += str(supportedSensor[1].shortname)  + " text,"	
			sqlInsertTemplate += str(supportedSensor[1].shortname)  + ","
			
		sqlCreateTable = sqlCreateTable[:sqlCreateTable.rfind(",")] + ")"
		#print sqlCreateTable
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
		#print sqlInsertTemplate
		
		time.sleep(3)

		if(self.port is None):
			return None
		
		#Loop until Ctrl C is pressed        
		try:
			nRunningTotalFuelConsumption = 0
			nStartTime = time.time()
			x = 0
			while True:
				current_time = time.time()
				#current_time = str(localtime.hour)+":"+str(localtime.minute)+":"+str(localtime.second)+"."+str(localtime.microsecond)
				#log_string = current_time + "\n"
				sqlInsert = sqlInsertTemplate + '"' + str(current_time) + '",'
				results = {}
				for supportedSensor in self.supportedSensorList:
					sensorIndex = supportedSensor[0]
					#print sensorIndex
					(name, value, unit) = self.port.sensor(sensorIndex)
					#log_string += name + " = " + str(value) + " " + str(unit) + "\n"
					#print value,type(value)
					sqlInsert += '"' + str(value) + '",'	
				
				
				sqlInsert = sqlInsert[:sqlInsert.rfind(",")] + ")"
				#print sqlInsert

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
					
				#print log_string,
				#time.sleep(0.5)
				

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
