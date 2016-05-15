#!/usr/bin/env python

import obd_io
import serial
import platform
import obd_sensors
import time
import os
import sqlite3
import sys
import HD44780
from gpiozero import Button
from obd_utils import scanSerial

class OBD_Capture():
	def __init__(self):
		self.port = None
		self.DisplayModeButton = Button(16)
		self.DisplayModeButton.when_pressed = self.DisplayModePressed
		self.cDisplayMode = "metric"
		self.nShutdownButtonPressed = False
		self.tShutdownTime = time.time()
		self.nCurrentSpeed = 0
		
	def DisplayModePressed(self):
		if self.nShutdownButtonPressed == True:
			if time.time() - self.tShutdownTime < 3:
				oLCD.clear()
				time.sleep(.1)
				oLCD.message("Shutting down...")
				#self.cursor.close()
				#self.conn.close()
				#time.sleep(0.5)
				os.system("sudo poweroff")	
		else:
			if (self.nCurrentSpeed == 0):
				oLCD.clear()
				time.sleep(.1)
				oLCD.message("Press within 3s \nto shutdown...")
				self.nShutdownButtonPressed = True
				self.tShutdownTime = time.time()
				return
			else:
				self.nShutdownButtonPressed = False
					
		if self.cDisplayMode == "metric":
			self.cDisplayMode = "usgal"
		elif self.cDisplayMode == "usgal":
			self.cDisplayMode = "impgal"
		elif self.cDisplayMode == "impgal":
			self.cDisplayMode = "metric_europe"
		else:
			self.cDisplayMode = "metric"

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
			print "Connected to " + self.port.port.name

	def is_connected(self):
		return self.port

	def LCDprint(self,cShortTerm,cLongTerm):
		oLCD.clear()
		time.sleep(.1)
		oLCD.message(cShortTerm + "\n" + cLongTerm)
		
	def FormatForDisplayMode(self,cInstance,nValue):
		nConvertedValue =  0
		if self.cDisplayMode == "metric":
			nConvertedValue = nValue
			cReturnValue = "{:5.2f}".format(nConvertedValue).lstrip()
			if cInstance == "immediate":
				cReturnValue += " l/100 km 3s"
			else:
				cReturnValue += " trip"
		elif self.cDisplayMode == "usgal":
			if nValue > 0:
				nConvertedValue = 378.5411784/(1.609344 * nValue)
			cReturnValue = "{:5.2f}".format(nConvertedValue).lstrip()
			if cInstance == "immediate":
				cReturnValue += " mpg US 3s"
			else:
				cReturnValue += " trip"
		elif self.cDisplayMode == "impgal":
			if nValue > 0:
				nConvertedValue = 454.609/(1.609344 * nValue)
			cReturnValue = "{:5.2f}".format(nConvertedValue).lstrip()
			if cInstance == "immediate":
				cReturnValue += " mpg Im 3s"
			else:
				cReturnValue += " trip"
		elif self.cDisplayMode == "metric_europe":
			if nValue > 0:
				nConvertedValue =  100/nValue
			cReturnValue = "{:5.2f}".format(nConvertedValue).lstrip()
			if cInstance == "immediate":
				cReturnValue += " km/l 3s"
			else:
				cReturnValue += " trip"
		else:
			cReturnValue = "No value given"
		
		return cReturnValue
		
	def ComputeFuelConsumption(self,lEmulate = False,nStartSec = 0):
		if lEmulate == False:
			nStartSec = time.time() - 1 	
		
		try:
			print nStartSec
			#cLimit = " and time_read > " + str(nStartSec) + " order by time_read desc limit 6)"
			cLimit = str(nStartSec) + " and time_read <= " + str(nStartSec + 5) + ' and speed > "0"'
			#print cLimit
			#self.cursor.execute('''SELECT avg((3600 * maf)/(9069.90 * speed)) FROM (select maf,speed from SensorReadings where speed > "0" and maf > "0" and rpm != "NODATA" ''' + cLimit)
			self.cursor.execute('''SELECT avg(fuelconsumption),speed FROM SensorReadings WHERE time_read >= ''' + cLimit)
			data = self.cursor.fetchone()
			#print data
			if data[0] == None:
				self.nCurrentSpeed = 0
				print "No data received in last polling period..."
			else:	
				self.nCurrentSpeed = data[1]
				print "Current speed: " + str(self.nCurrentSpeed)
				#self.cursor.execute('''SELECT avg((3600 * maf)/(9069.90 * speed)) FROM (select maf,speed from SensorReadings where speed > "0" and maf > "0" and rpm != "NODATA" and time_read >= ''' + cLimit + ")")
				#data = self.cursor.fetchone()
		except sqlite3.OperationalError,msg:
			return msg
		
		if data[0] != None:
			nAvgFuelConsumption = data[0]
						
			try:
				nAvgFuelConsumption = float(nAvgFuelConsumption)
				return "{:5.2f}".format(nAvgFuelConsumption).lstrip()
			except TypeError:
				return "No data"	
				 	
		else:
			return "Idling..."
		
	def is_number(self,DataToTest):
		try:
			float(DataToTest)
			return True
		except ValueError:
			return False
		
	def capture_data(self,lEmulate = False):
		if lEmulate == False:
			#print "false"
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
			
			sqlCreateTable += "FuelConsumption text)"	
			#sqlCreateTable = sqlCreateTable[:sqlCreateTable.rfind(",")] + ")"
			
			try:
				self.cursor.execute(sqlCreateTable)
				self.conn.commit()
				self.cursor.execute('''CREATE INDEX time_read_index on SensorReadings(time_read)''')
				cMessage = " New database: \n" + cNewDatabase
			except sqlite3.OperationalError,msg:
				cMessage = msg
				
			oLCD.clear()
			time.sleep(.1)
			oLCD.message(cMessage)
			
			#sqlInsertTemplate = sqlInsertTemplate[:sqlInsertTemplate.rfind(",")] + ") VALUES ("
			sqlInsertTemplate += "FuelConsumption) VALUES ("
			print "sqlInsertTemplate = " + sqlInsertTemplate 
			time.sleep(1.0)
	
			if(self.port is None):
				return None
			
		#Loop until further notice  
		try:
			print "Beginning try statement"
			nRunningTotalFuelConsumption = 0
			if lEmulate == False:
				nStartTime = time.time()
			else:
				#Change the number on the following line to the database you wish to examine.
				self.conn = sqlite3.connect("obdii00013.db")
				self.cursor = self.conn.cursor()
				self.cursor.execute('''SELECT time_read from SensorReadings limit 1''')
				data = self.cursor.fetchone()
				current_time = data[0]
				nStartTime = data[0]
				print nStartTime
				self.cursor.execute('''SELECT time_read from SensorReadings order by time_read desc limit 1''')
				data = self.cursor.fetchone()
				time_of_last_row = data[0]
				
			x = 0
			y = 0
			print "End try statement, beginning while loop"
			while True:
				if lEmulate == False:
					current_time = time.time()
					sqlInsert = sqlInsertTemplate + '"' + str(current_time) + '",'
					#results = {}
					nSpeed = 0
					for supportedSensor in self.supportedSensorList:
						sensorIndex = supportedSensor[0]
						(name, value, unit) = self.port.sensor(sensorIndex)
						sqlInsert += '"' + str(value) + '",'
						#print "Name: " + name
						#print "Value: " + str(value)
						#print "Unit: " + unit
						if name.strip() == "Vehicle Speed":
							nSpeed = value
						if name.strip() == "Air Flow Rate (MAF)":
							nMaf = value
					if nSpeed > 0:
						nFuelConsumption = (3600 * nMaf)/(9069.90 * nSpeed)
					else:
						nFuelConsumption = 0
							
					#sqlInsert = sqlInsert[:sqlInsert.rfind(",")] + ")"
					sqlInsert += '"' + str(nFuelConsumption) + '")'
					print "sqlInsert = " + sqlInsert
					
					try:
						self.cursor.execute(sqlInsert)
						self.conn.commit()
					except sqlite3.OperationalError,msg:
						oLCD.clear()
						oLCD.message(msg)	
						continue
				
				cInstantaneousAverageDisplay = "No data"  #default value
				cTripAverageDisplay = "No data" #default value
				cFuelConsumption = self.ComputeFuelConsumption(lEmulate,current_time)
				if lEmulate:
					x += 1
				else:
					if cFuelConsumption != "No data" and cFuelConsumption != "Idling":
						x += 1
				print cFuelConsumption		
				if (x > 0):
					if (self.is_number(cFuelConsumption)):
						nInstantaneousAverage = float(cFuelConsumption)
						cInstantaneousAverageDisplay = self.FormatForDisplayMode("immediate",nInstantaneousAverage)
						nRunningTotalFuelConsumption += nInstantaneousAverage
						y += 1
					else:
						cInstantaneousAverageDisplay = cFuelConsumption	
					if y > 0:
						nTripAverage = nRunningTotalFuelConsumption/y
						cTripAverageDisplay = self.FormatForDisplayMode("long",nTripAverage) + " " +"{:3.0f}".format((current_time - nStartTime)/60).lstrip() + "m"
					#print x
					#print y
					print cTripAverageDisplay
					print current_time
				if int(x)%5 == 0:
					self.LCDprint(cInstantaneousAverageDisplay,cTripAverageDisplay)
				if lEmulate:
					current_time = nStartTime + x
					if current_time > time_of_last_row:
						print "End of file reached"
						exit()
					time.sleep(1)

		except KeyboardInterrupt:
			if lEmulate == False:
				self.port.close()
			print("Stopped")
			
if __name__ == "__main__":
	
	lEmulate = False
	nTotalArgs = len(sys.argv)
	if nTotalArgs > 1:
		cArgumentPassed = str(sys.argv[1])
		if cArgumentPassed == "emulate":
			lEmulate = True
			
	#if not lEmulate:
		##Creating new stdout redirection file
		#for kounter in range(10000):
			#cKounter = "{0:05d}".format(kounter)
			#cNewStdOutLog = "stdoutlog" + cKounter + ".txt"
			#if not (os.path.exists(cNewStdOutLog)):
				#break
					
		#sys.stdout = open(cNewStdOutLog,'w')
		
	oLCD = HD44780.HD44780()
	time.sleep(1) #Apparently, the class invocation takes some time to set up
	oLCD.clear()
	oLCD.message(" Initializing..")
	o = OBD_Capture()
	
	if lEmulate == True:
		o.capture_data(True)
	else:	
		try:
			o.connect()
		except OSError:
			oLCD.clear()
			oLCD.message(" Unable to find serial port")
			print "Unable to find serial port"
			exit()
		time.sleep(1)
		if not o.is_connected():
			print "Not connected"
			oLCD.clear()
			oLCD.message(" Err: Not connected \nto OBDII...")
			time.sleep(3)
			exit()
		else:
			o.capture_data()
