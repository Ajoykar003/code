from datetime import datetime
import subprocess
import time
import logging as log
import json
import os

log.basicConfig(filename='/var/tmp/weather.log', filemode='w', level=log.INFO, format='[%(asctime)s]- %(message)s', datefmt='%d-%m-%Y %I:%M:%S %p')

path = "/etc/entomologist/"
with open(path + "ento.conf",'r') as file:
	data=json.load(file)
DEVICE_SERIAL_ID = data["device"]["SERIAL_ID"]
STORAGE_PATH=data["device"]["WEATHER_STORAGE_PATH"]

def getHTS221Data(hts221SubprocessOutput):
	hts221SubprocessOutput = str(hts221SubprocessOutput)[2:-2].split("\\n")
	hts221SubprocessOutput = [eachEntry.split(":")[1] for eachEntry in hts221SubprocessOutput]
	HUMIDITY = hts221SubprocessOutput[0].split(" ")[1]
	TEMP_C = hts221SubprocessOutput[1].split(" ")[1]
	TEMP_F = hts221SubprocessOutput[2].split(" ")[1]
	return (HUMIDITY, TEMP_C, TEMP_F)

def getVEML7700Data(VEML7700SubprocessOutput):
	LUX = str(VEML7700SubprocessOutput)[2:len(VEML7700SubprocessOutput)].split("\\n")[0].split(":")[1].split(" ")[1]
	return LUX

def weather():
	
	p = subprocess.Popen("/usr/sbin/weather/hts221", stdout=subprocess.PIPE, shell=True) # Use script file instead.
	(output, err) = p.communicate()
	HUMIDITY, TEMP_C, TEMP_F = getHTS221Data(output)
	
	q = subprocess.Popen("/usr/sbin/weather/VEML7700", stdout=subprocess.PIPE, shell=True)
	(output, err) = q.communicate()
	LUX = getVEML7700Data(output)

	Timestamp = datetime.now()
	Timestamp_time = Timestamp.strftime("%a %Y-%m-%d %H:%M:%S IST")
	
	Filename_time = str(Timestamp.strftime("%Y-%m-%d_%H"))
	File_path = f"{STORAGE_PATH}weather_{Filename_time}_{DEVICE_SERIAL_ID}.csv"

	if os.path.exists(File_path):
		file = open(File_path, "a")
	else:
		file = open(File_path, "a")
		file.writelines("TimeStamp,DeviceId,Relative_Humidity(%),Temperature(C),Temperature(F),Light_intensity(Lux)\n")

	output = str(Timestamp_time) + "," + DEVICE_SERIAL_ID + "," + HUMIDITY + "," + TEMP_C + ","+ TEMP_F + "," + LUX + "\n"

	file.writelines(output)
	file.close()

	time.sleep(30)

while True:
	try:
		weather()
	except Exception as e:
		log.info(e)
		time.sleep(5)