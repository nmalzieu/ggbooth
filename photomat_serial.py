import serial
import re
import os


class PhotoMatonSerial:
	greenClickCallback = None
	redClickCallback = None
	
	def __init__(self, port) :
		self.ser = serial.Serial()
		self.ser.baudrate = 9600
		self.ser.port = port

	def onGreenClick(self, callback):
		self.greenClickCallback = callback

	def onRedClick(self, callback):
		self.redClickCallback = callback

	def open(self):
		self.ser.open()

		if not self.ser.isOpen():
			raise "Could not open connexion to the Arduino"

		print "Serial connexion is opened. Waiting for input..."

		while True:
			raw = self.ser.readline()
			
			if raw == '':
				continue

			m = re.search('DATA%(.*?)%DATA', raw)
			 
			if m.group(1) == 'RED_CLICK':
				if self.redClickCallback != None:
					self.redClickCallback()	
					
			elif m.group(1) == 'GREEN_CLICK':
				if self.greenClickCallback != None:
					self.greenClickCallback()


def greenClick():
    print "GREEN"
    open('green', 'a').close()
	

def redClick():
    print "RED"
    open('red', 'a').close()

pyMathon = PhotoMatonSerial('/dev/tty.usbmodemfd121')
pyMathon.onRedClick(redClick)
pyMathon.onGreenClick(greenClick)
pyMathon.open()
