"""
Author:		Patrick Tafoya
Purpose:	Test full ECS
			For this test i have the sensors hooked up to the following tca channels
			
			bus 0:
				LIDAR lite v3	5v
			bus 1:
				BNO055 at 0x28
				BNO055 at 0x29
				BMP280 at 0x77
			bus 2:
				BME280 at 0x76 LPV
			bus 3:
				MLX90614 at 0x5B
				ADS1115 at 0x48	gain = 1 (4.096V MAX)
			bus 4:
				BME280 at 0x77
"""
import smbus
from time import sleep, clock
from mlx90614 import MLX90614
from Adafruit_BNO055 import BNO055
import Adafruit_ADS1x15
from HyperlynxBMP280 import BMP280
from Adafruit_BME280 import BME280
import Lidar
import RPi.GPIO

class HyperlynxECS():
	def __init__(self, bus_num=1):
		self.MUX_ADDR = 0x70											#I2C ADDRESS FOR TCA9548A MULTIPLEXER
		self.IR_ADDR = 0x5B												#I2C ADDRESS FOR MLX90614 IR THERMOMETER
		self.IMU_ADDR1 = 0x28											#I2C ADDRESS 1 FOR BNO055 ABSOLUTE ORIENTATION
		self.IMU_ADDR2 = 0x29											#I2C ADDRESS 2 FOR BNO055 ABSOLUTE ORIENTATION
		self.BMP_ADDR = 0x77											#I2C ADDRESS FOR BMP280 PRESSURE SENSOR
		self.BME_ADDR1 = 0x77											#I2C ADDRESS 1 FOR BME280 PRESSURE SENSOR
		self.BME_ADDR2 = 0x76											#I2C ADDRESS 2 FOR BME280 PRESSURE SENSOR
		self.LID_ADDR = 0x62											#I2C ADDRESS FOR LIDAR LITE V3
		self.ADC_ADDR = 0x48											#I2C ADDRESS FOR ADS1115 ADC
		self.METER2G = (3.28084/32.2)									#CONVERSION: METER TO FEET => FEET/G FOR ACCELERATION
		self.VOLT2PSI = 94.697											#CONVERSION: VOLTS READ BY ADC TO PSI FOR HONEYWELL PRESSURE SENSOR
		self.PRESSURE = 2												#ADC PIN FOR HONEYWELL PRESSURE SENSOR
		self.VOLT = 0													#ADC PIN FOR ATTOPILOT VOLTAGE READ
		self.AMP = 1													#ADC PIN FOR ATTOPILOT CURRENT READ
		self.ADC_GAIN = 1												#GAIN SETTING FOR ADC: READS UP TO 4.096 V
		self.ADC_CONVERT = (4.096/32767.0)								#CONVERT ADC 16BIT SIGNED RESOLUTION TO VOLTAGE LEVEL FOR GAIN OF 1
		self.vRatio = 4.13												#ATTOPILOT RATIO: VOLTAGE TRANSMITTED TO ACTUAL VOLTAGE READING
		self.iRatio = 1													#ATTOPILOT RATIO: VOLTAGE TRANSMITTED TO ACTUAL CURRENT READING
		self.PASC2PSI = (1/6894.757)
		self.IO = RPi.GPIO												#INITIALIZE RPi.GPIO LIBRARY TO CONTROL DROK SWITCHES
		self.NOsolPIN = 17												#DROK SIGNAL PIN FOR NORMALLY OPEN SOLENOID
		self.NCsol1PIN = 27												#DROK SIGNAL PIN FOR NORMALLY CLOSED SOLENOID RESERVIOR 1
		self.NCsol2PIN = 22												#DROK SIGNAL PIN FOR NORMALLY CLOSED SOLENOID RESERVOIR 2
		self.CoolPumpPIN = 5											#DROK SIGNAL PIN FOR COOLANT PUMP
		self.greenPIN = 6												#DROK SIGNAL PIN FOR GREEN LED
		self.contactorPIN1 = 13											#DROK SIGNAL PIN FOR CONTACTOR 1
		self.contactorPIN2 = 18											#DROK SIGNAL PIN FOR CONTACTOR 2
		self.bus = smbus.SMBus(bus_num)									#OPEN I2C BUS
		self.IO.setmode(self.IO.BCM)									#BCM MODE USES BROADCOM SOC CHANNEL NUMBER FOR EACH PIN
		self.IO.setwarnings(False)										#TURN OFF WARNINGS TO ALLOW OVERIDE OF CURRENT GPIO CONFIGURATION
		self.Y1OFFSET = 0
		self.Y2OFFSET = 0
		self.Z1OFFSET = 0
		self.Z2OFFSET = 0
		self.currentBus = 10											#VARIABLE TO KEEP TRACK OF WHICH TCA CHANNEL IS OPEN, 10 WILL BE NO CHANNEL AS 0 IS A SPECIFIC CHANNEL
		self.tcaLIDAR = 0												#TCA CHANNEL FOR LIDAR
		self.tcaNOSE = 1												#TCA CHANNEL FOR NOSE AVIONICS
		self.tcaPVL = 2													#TCA CHANNEL FOR LEFT PV AVIONICS
		self.tcaPVR = 3													#TCA CHANNEL FOR RIGHT PV AVIONICS 1
		self.tcaPVR2 = 4												#TCA CHANNEL FOR RIGHT PV AVIONICS 2
		self.connectAttempt = 5
		try:															#ESTABLISH CONNECTION TO MULTIPLEXER
			self.bus.write_byte(self.MUX_ADDR, 0)
			print("TCA I2C Multiplexer Ready")
		except IOError:
			print("Connection Error with TCA I2C Multiplexer")
			while True:
				pass													#IF UNABLE TO CONNECT TO MULTIPLEXER, STALL PROGRAM
		self.closeAllBus()												#RESET TCA9548A MULTIPLEXER TO CLOSE ALL CHANNELS AT STARTUP
		
	"""SETUP ALL AVIONICS SENSORS ON THE I2C BUS"""
	def initializeSensors(self):
		try:
			for x in range(0, self.connectAttempt):
				self.openBus(self.tcaLIDAR)								#OPEN CHANNEL ON TCA
				if(self.currentBus == self.tcaLIDAR):
					break
				sleep(0.5)
		except IOError:
			print("Connection error with TCA Multiplexer")
			return 0;
		try:
			self.Lidar = Lidar.Lidar_Lite()								#CREATE OBJECT FOR LIDAR LITE V3
			self.bus.write_quick(self.LID_ADDR)							#QUICK WRITE TO TEST CONNECTION TO I2C BUS
			print("Lidar Ready")
		except IOError:
			print("Connection error with Lidar")						#PRINT ERROR IF UNABLE TO CONNECT
			return 0
		try:
			for x in range(0, self.connectAttempt):
				self.openBus(self.tcaNOSE)								#OPEN CHANNEL ON TCA
				if(self.currentBus == self.tcaNOSE):
					break
				sleep(0.5)
		except IOError:
			print("Connection error with TCA Multiplexer")
			return 0

		try:
			for x in range(0, self.connectAttempt):
				self.IMU1 = BNO055(address=self.IMU_ADDR1)				#CREATE OBJECT FOR BNO055 AT ADDRESS 1 
				if(self.IMU1.begin(mode=0x08)):							#CHECK FOR CONNECTION TO I2C BUS AND SET IMU OPR MODE (MAG DISABLED)
					while(self.IMU1.get_calibration_status()[1] != 3):
						pass											#WAIT FOR GYRO CALIBRATION COMPLETE
					print("IMU1 Ready")
					break
				sleep(0.5)
		except IOError:
			print("Connection error with IMU1")
			#return 0
		try:
			self.Y1OFFSET = self.getOrientation(1)[1]
			print("IMU1 Y offset angle set")
		except IOError:
			print("IMU1 Y offset angle not set")
		try:
			self.Z1OFFSET = self.getOrientation(1)[2]
			print("IMU1 Z offset angle set")
		except IOError:
			print("IMU1 Z offset angle not set")
		try:
			for x in range(0, self.connectAttempt):
				self.IMU2 = BNO055(address=self.IMU_ADDR2)				#CREATE OBJECT FOR BNO055 AT ADDRESS 2
				if(self.IMU2.begin(mode=0x08)):							#CHECK FOR CONNECTION TO I2C BUS AND SET IMU OPR MODE (MAG DISABLED)
					while(self.IMU2.get_calibration_status()[1] != 3):
						pass											#WAIT FOR GYRO CALIBRATION COMPLETE
					print("IMU2 Ready")
					break
				sleep(0.5)
		except IOError:
			print("Connection Error with IMU2")
			#return 0
		try:
			self.Y2OFFSET = self.getOrientation(2)[1]
			print("IMU2 Y offset angle set")
		except IOError:
			print("IMU2 Y offset angle not set")
		try:
			self.Z1OFFSET = self.getOrientation(2)[2]
			print("IMU2 Z offset angle set")
		except IOError:
			print("IMU2 Z offset angle not set")
		try:
			for x in range(0, self.connectAttempt):
				self.BMP = BMP280(address=self.BMP_ADDR)				#CREATE OBJECT FOR BMP280
				if(self.BMP.read_raw_temp()):							#ATTEMPT READING FROM BMP
					print("BMP Ready")
					break
				sleep(0.5)
		except IOError:
			print("Connection Error with BMP")
			#return 0
		try:
			for x in range(0, self.connectAttempt):
				self.openBus(self.tcaPVL)								#OPEN CHANNEL ON TCA
				if(self.currentBus == self.tcaPVL):
					break
				sleep(0.5)
		except IOError:
			print("Connection error wit TCA Multiplexer")
			return 0
		try:
			for x in range(0, self.connectAttempt):
				self.BMEL = BME280(address=self.BME_ADDR2)				#CREATE OBJECT FOR BME280 AT ADDRESS 2
				if(self.BMEL.read_raw_temp()):
					print("BME LPV Ready")
					break
				sleep(0.5)
		except IOError:
			print("Connection Error with BME2 LPV")
			#return 0
		try:
			for x in range(0, self.connectAttempt):
				self.openBus(self.tcaPVR)								#OPEN TCA CHANNEL
				if(self.currentBus == self.tcaPVR):
					break
				sleep(0.5)
		except IOError:
			print("Connection error with TCA Multiplexer")
			return 0
		try:
			for x in range(0, self.connectAttempt):
				self.Therm = MLX90614(address=self.IR_ADDR)				#CREATE OBJECT FOR MLX90614 IR THERMOMETER
				if(self.Therm.check_connect):							#CHECK CONNECTION
					print("MLX90614 Ready")
					break
				sleep(0.5)
		except IOError:
			print("Connection Error with Therm")
			#return 0
		try:
			self.ADC = Adafruit_ADS1x15.ADS1115(address=self.ADC_ADDR, busnum=1)#CREATE OBJECT FOR ADS1115 ADC
			print("ADC Ready")		
		except IOError:
			print("Connection error with ADS ADC")
			#return 0
		try:
			for x in range(0, self.connectAttempt):
				self.openBus(self.tcaPVR2)								#OPEN CHANNEL ON TCA
				if(self.currentBus == self.tcaPVR2):
					break
				sleep(0.5)
		except IOError:
			print("Connection error with TCA Multiplexer")
			return 0
		try:
			for x in range(0, self.connectAttempt):
				self.BMER = BME280(address=self.BME_ADDR1)				#CREATE  OBJECT FOR BME280 AT ADDRESS 2
				if(self.BMER.read_raw_temp()):
					print("BME RPV Ready")
					break
				sleep(0.5)
		except IOError:
			print("Connection Error with BME RPV")
			#return 0
		return 1
			
	"""CLOSE ALL CHANNELS ON THE TCA"""
	def closeAllBus(self):
		self.bus.write_byte(self.MUX_ADDR, 0)							#WRITE ALL BITS ON TCA CHANNEL SELECT REGISTER LOW
		self.currentBus = 10											#UPDATE CURRENT OPEN CHANNEL
	"""OPEN SPECIFIC CHANNEL ON THE TCA"""
	def openBus(self, bus_num):											#PARAMETER IS DESIRED TCA CHANNEL TO OPEN
		self.bus.write_byte(self.MUX_ADDR, (1<<bus_num))				#WRITE SPECIFIED CHANNEL BIT HIGH ON TCA SELECT REGISTER
		self.currentBus = bus_num										#UPDATE CURRENT OPEN CHANNEL
	"""FETCH LV BATTERY TEMPERATURE"""	
	def getBatteryTemp(self):
		if(self.currentBus != self.tcaPVR):
			try:
				self.openBus(self.tcaPVR)								#CHECKS FOR CURRENT OPEN CHANNEL TO SAVE TIME SELECTING IF IT IS ALREADY OPEN, IF ALREADY NOT OPENED, OPEN IT
			except IOError:
				return 0
		sleep(0.001)													#RETURNS A ZERO IF CANNOT CONNECT TO THE TCA
		try:
			data = self.Therm.get_obj_temp_C()							#FETCH OBJECT TEMP
		except IOError:
			data = 0													#SETS AS ZERO IF CANNOT CONNECT TO MLX90614
		return data														#RETURNS TEMPERATURE READING IN DEGREES CELSIUS
	"""FETCH ORIENTATION"""												#PARAMETER IS DESIRED IMU (1 OR 2)
	def getOrientation(self, imu_num):
		if(self.currentBus != self.tcaNOSE):
			try:
				self.openBus(self.tcaNOSE)								#CHECK IF BUS IS OPENED, IF IT IS NOT, OPEN IT
			except IOError:
				return [0, 0, 0]										#RETURNS TUPLE OF ZEROS IF CANNOT CONNECT TO TCA
		if(imu_num == 1):
			try:
				data = self.IMU1.read_euler()							#READS X, Y AND Z ORIENTATION IN DEGREES AND RETURNS AS TUPLE
			except IOError:
				data = [0, 0, 0]										#SETS AS ZEROS IF CANNOT CONNECT TO BNO055
			return data
		elif(imu_num == 2):
			try:
				data = self.IMU2.read_euler()
			except IOError:
				data = [0, 0, 0]
			return data
		else:
			print("Illegal Selection")
			return 0
	"""FETCH LINEAR ACCELERATION"""										#PARAMETER IS DESIRED IMU (1 OR 2)										
	def getAcceleration(self, imu_num):
		if(self.currentBus != self.tcaNOSE):
			try:
				self.openBus(self.tcaNOSE)
			except IOError:
				return 0
		if(imu_num == 1):
			try:
				data = self.IMU1.read_linear_acceleration()
			except IOError:
				return 0
			return data[0] * self.METER2G								#RETURNS ACCELERATION IN G'S
		elif(imu_num == 2):
			try:
				data = self.IMU2.read_linear_acceleration()
			except IOError:
				return 0
			return data[0] * self.METER2G								#RETURNS ACCELERATION IN G'S
		else:
			print("Illegal Selection")
			return 0		
	"""FETCH LIDAR DISTANCE READING"""										
	def getLidarDistance(self):
		if(self.currentBus != self.tcaLIDAR):
			try:
				self.openBus(self.tcaLIDAR)
			except IOError:
				return 0												#RETURNS ZERO IF CANNOT CONNECT TO TCA
		try:
			data = self.Lidar.getDistance()								#FETCH DISTANCE
		except IOError:
			data = 0													#SETS AS ZERO IF CANNOT CONNECT TO LIDAR
		return data * 0.0328084											#RETURNS DISTANCE IN FEET
	"""FETCH TUBE PRESSURE"""	
	def getTubePressure(self):
		if(self.currentBus != self.tcaNOSE):
			try:
				self.openBus(self.tcaNOSE)
			except IOError:
				return 0												#RETURNS ZERO IF CANNOT CONNECT TO TCA
		try:
			data = self.BMP.read_pressure()								#FETCH PRESSURE
		except IOError:
			data = 0													#SETS AS ZERO IF CANNOT CONNECT TO BMP
		return data														#RETURNS PRESSURE IN PSI
	"""FETCH TUBE TEMPERATURE"""	
	def getTubeTemp(self):
		if(self.currentBus != self.tcaNOSE):
			try:
				self.openBus(self.tcaNOSE)
			except IOError:
				return 0												#RETURNS ZERO IF CANNOT CONNECT TO TCA
		try:
			data = self.BMP.read_temperature()							#FETCH TEMPERATURE
		except IOError:
			data = 0													#SETS AS ZERO IF CANNOT CONNECT TO BMP
		return data														#RETURNS TEMPERATURE IN DEGREES CELSIUS
	"""FETCH BME PRESSURE"""											#PARAMETER IS DESIRED BME (1 = RIGHT PV, 2 = LEFT PV)
	def getBMEpressure(self, vessel):
		if(vessel == 1):
			if(self.currentBus != self.tcaPVR):
				try:
					self.openBus(self.tcaPVR)
				except IOError:
					return 0											#RETURNS ZERO IF CANNOT CONNECT TO TCA
			try:
				data = self.BMER.read_pressure()						#FETCH PRESSURE
			except IOError:
				data = 0												#SETS AS ZERO IF CANNOT CONNECT TO BME
			return data	* self.PASC2PSI									#RETURNS PRESSURE IN PSI
		elif(vessel == 2):
			if(self.currentBus != self.tcaPVL):
				try:
					self.openBus(self.tcaPVL)
				except IOError:
					return 0
			try:
				data = self.BMEL.read_pressure()
			except IOError:
				data = 0
			return data * self.PASC2PSI
		else:
			print("Illegal vessel")
			data = 0
			return data
	"""FETCH BME TEMPERATURE"""											#PARAMETER IS DESIRED BME (1 = RIGHT PV, 2 = LEFT PV) 		
	def getBMEtemperature(self, vessel):
		if(vessel == 1):
			if(self.currentBus != self.tcaPVR2):
				try:
					self.openBus(self.tcaPVR2)
				except IOError:
					return 0											#RETURNS ZERO IF CANNOT CONNECT TO TCA
			try:
				data = self.BMER.read_temperature()						#FETCH TEMPERATURE
			except IOError:
				data = 0												#SETS AS ZERO IF CANNOT CONNECT TO BME
			return data													#RETURNS TEMPERATURE IN DEGREES CELSIUS
		elif(vessel == 2):
			if(self.currentBus != self.tcaPVL):
				try:
					self.openBus(self.tcaPVL)
				except IOError:
					return 0
			try:
				data = self.BMEL.read_temperature()
			except IOError:
				return 0
			return data
		else:
			print("Illegal Selection")
			return 0
	"""FETCH LV BATTERY VOLTAGE LEVEL"""		
	def getVoltageLevel(self):
		if(self.currentBus != self.tcaPVR):
			try:
				self.openBus(self.tcaPVR)
			except IOError:
				return 0												#RETURNS ZERO IF CANNOT CONNECT TO TCA
		try:
			data = self.ADC.read_adc(self.VOLT, self.ADC_GAIN)			#READ VOLTAGE PIN SET ON ADC
		except IOError:
			data = 0													#SETS AS ZERO IF CANNOT CONNECT TO ADC
		return data * self.ADC_CONVERT * self.vRatio					#CONVERTS ADC BITS TO ACTUAL VOLTAGE SENT BY ATTOPILOT AND SCALES TO VOLTAGE READ BY ATTOPILOT, RETURNS VOLTAGE
	"""FETCH LV BATTERY CURRENT DRAW"""#DOES NOT WORK YET, SOURCING NEW SENSOR	
	def getCurrentLevel(self):
		if(self.currentBus != self.tcaPVR):
			try:
				self.openBus(self.tcaPVR)
			except IOError:
				return 0
		try:
			data = self.ADC.read_adc(self.AMP, self.ADC_GAIN)
		except IOError:
			data = 0
		return data * self.ADC_CONVERT * self.iRatio
	"""FETCH BRAKE LINE PRESSURE"""	
	def getBrakePressure(self):
		if(self.currentBus != self.tcaPVR):
			try:
				self.openBus(self.tcaPVR)
			except IOError:
				return 0												#RETURNS ZERO IF CANNOT CONNECT TO TCA
		try:
			data = self.ADC.read_adc(self.PRESSURE, self.ADC_GAIN)		#READ PRESSURE PIN SET ON ADC
		except IOError:
			data = 0													#SETS AS ZERO IF CANNOT CONNECT TO ADC
		return data * self.ADC_CONVERT * self.VOLT2PSI					#CONVERTS ADC BITS TO ACTUAL VOLTAGE SENT BY HONEYWELL AND CONVERTS VOLTAGE TO PSI, RETURNS PRESSURE IN PSI
	
	def initializeDROK():
		self.IO.setup(self.contactorPIN1, self.IO.OUT, initial=self.IO.LOW)#SET CONTACTOR1 PIN AS OUTPUT, INITIALIZE LOW
		self.IO.setup(self.greenPIN, self.IO.OUT, initial=self.IO.LOW)	#SET GREEN LED PIN AS OUTPUT, INITIALIZE LOW
		self.IO.setup(self.contactorPIN2, self.IO.OUT, initial=self.IO.LOW)	#SET CONTACTOR 2 PIN AS OUTPUT, INITIALIZE LOW
		self.IO.setup(self.NOsolPIN, self.IO.OUT, initial=self.IO.LOW)	#SET NO SOLENOID PIN AS OUTPUT, INITIALIZE LOW
		self.IO.setup(self.NCsol1PIN, self.IO.OUT, initial=self.IO.LOW)	#SET NC SOLENOID RES 1 PIN AS OUTPUT, INITIALIZE LOW
		self.IO.setup(self.NCsol2PIN, self.IO.OUT, initial=self.IO.LOW)	#SET NC SOLENOID RES 2 PIN AS OUTPUT, INITIALIZE LOW
		self.IO.setup(self.coolPumpPIN, self.IO.OUT, initial=self.IO.LOW)#SET COOLANT PUMP PIN TO OUTPUT, INITIALIZE LOW
			
	def switchGreenLED(self, status):
		if(status == 0):
			self.IO.output(self.greenPIN, self.IO.LOW)
		else:
			self.IO.output(self.greenPIN, self.IO.HIGH)
			
	#Switches solenoid DROKs. Parameters(solenoid: 1 = NC res 1, 2 = NC res 2, 3 = NO, status: 0 = LOW, 1 = HIGH)
	def switchSolenoid(self, solednoid, status):
		if(solenoid == 1):
			if(status == 0):
				self.IO.output(self.NCsol1PIN, self.IO.LOW)
			elif(status == 1):
				self.IO.output(self.NCsol1PIN, self.IO.HIGH)
		elif(solenoid == 2):
			if(status == 0):
				self.IO.output(self.NCsol2PIN, self.IO.LOW)
			elif(status == 1):
				self.IO.output(self.NCsol2PIN, self.IO.HIGH)
		elif(solenoid == 3):
			if(status == 0):
				self.IO.output(self.NOsolPIN, self.IO.LOW)
			elif(status == 1):
				self.IO.output(self.NOsolPIN, self.IO.LOW)
				
	def switchCoolantPump(self, status):
		if(status == 0):
			self.IO.output(self.coolPumpPIN, self.IO.LOW)
		else:
			self.IO.output(self.coolPumpPIN, self.IO.HIGH)
			
	#SWITCHES CONTACTOR DROKS. PARAMETERS(contactor: 1 = Contactor 1; 2 = Contactor 2, status: 0 = LOW; 1 = HIGH
	#RED LED WILL LIGHT WHEN BOTH CONTACTORS ARE SWITCHED ON
	def switchContactor(self, contactor, status):
		if(contactor == 1):
			if(status == 0):
				self.IO.output(self.contactorPIN1, self.IO.LOW)
			elif(status == 1):
				self.IO.output(self.contactorPIN1, self.IO.HIGH)
		elif(contactor == 2):
			if(status == 0):
				self.IO.output(self.contactorPIN2, self.IO.HIGH)
			elif(status == 1):
				self.IO.output(self.contactorPIN2, self.IO.HIGH)
			
				
	
		
if __name__ == '__main__':
	system = HyperlynxECS()
	if(system.initializeSensors()):
		while True:
			startTime = clock()
			distance = system.getLidarDistance()
			battTemp = system.getBatteryTemp()
			temp2 = system.getBMEtemperature(2)
			press2 = system.getBMEpressure(2)
			voltage = system.getVoltageLevel()
			current = system.getCurrentLevel()
			brakePressure = system.getBrakePressure()
			accel1 = system.getAcceleration(1)
			accel2 = system.getAcceleration(2)
			orient1 = system.getOrientation(1)
			orient2 = system.getOrientation(2)
			tubepress = system.getTubePressure()
			tubetemp = system.getTubeTemp()
			temp1 = system.getBMEtemperature(1)
			press1 = system.getBMEpressure(1)
			endTime = clock() - startTime
			print(endTime)
			print("%.2f C\t"%battTemp, "%.2f G\t"%accel1, "%.2f G"%accel2)
			print("X: %.2f\t"%orient1[0], "Y: %.2f\t"%orient1[1], "Z: %.2f"%orient1[2])
			print("X: %.2f\t"%orient2[0], "Y: %.2f\t"%orient2[1], "Z: %.2f"%orient2[2])
			print("PVL: %.2f psi\t"%press1, "%.2f C\t"%temp1, "PVR: %.2f psi\t"%press2, "%.2f C"%temp2)
			print("Tube: %.2f psi\t"%tubepress, "%.2f C"%tubetemp)
			print("%.2f V\t"%voltage, "%.2f A"%current)
			print("Brakes: %.2f psi" % brakePressure)
			print("\n")
			#sleep(0.05)
