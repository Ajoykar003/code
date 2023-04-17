import time
import os
import json
from datetime import datetime
import requests
import subprocess
import logging as log

time.sleep(10)
log.basicConfig(filename='/var/tmp/sync.log', filemode='w', level=log.INFO, format='[%(asctime)s]- %(message)s', datefmt='%d-%m-%Y %I:%M:%S %p')

global scriptStatus
scriptStatus=False
path = "/etc/entomologist/"
def entoDataWriter(parent,key,value):
    data=None
    with open(path + "ento.conf",'r') as file:
        data=json.load(file)
    data[parent][key]=value
    with open(path + "ento.conf",'w') as file:
        file.write(json.dumps(data,indent=4))

def testDevice(duration):
    log.info("Started testing the device")
    global scriptStatus
    if not scriptStatus:
        #start the services
        subprocess.call(["systemctl","restart","cam"])
        subprocess.call(["systemctl","restart","cloud"])
        writeInScriptStatus(True)
        log.info("Script restarted successfully of cam and cloud")
    log.info("Device is in testing state now")
    while duration:
        duration-=1
        time.sleep(1)
    log.info("Testing completed fully")
    entoDataWriter('device','TEST_FLAG','False')

def writeInScriptStatus(val): 
    global scriptStatus
    data=None
    with open(path + "scriptStatus.json",'r') as file:
        data=json.load(file)
    with open(path + "scriptStatus.json",'w') as file:
        data['status']=val
        file.write(json.dumps(data,indent=2))
        scriptStatus=val
    log.info(f"Writing in scriptstatus {val}")

def checkProvisonState():
    SENSOR_PATH = "/media/mmcblk1p1/sensor_upload"
    if not os.path.exists(SENSOR_PATH):
        print("Creating sensor path")
        os.mkdir(SENSOR_PATH)
    BUFFER_IMAGES_PATH = "/media/mmcblk1p1/upload"
    if not os.path.exists(BUFFER_IMAGES_PATH):
        print("Creating images path")
        os.mkdir(BUFFER_IMAGES_PATH)
    COUNT_PATH = "/media/mmcblk1p1/count_upload"
    if not os.path.exists(COUNT_PATH):
        print("Creating count path")
        os.mkdir(COUNT_PATH)
    log.info("checking Provison state")
    while True:
        data=None
        with open(path + "ento.conf",'r') as file:
            data=json.load(file)

        if data['device']['PROVISION_STATUS']=='True':
            log.info("Device Provisoned")
            break
        else:
            log.info("Trying For Provison")
            try:
                #call for provisoning script
                subprocess.call(["python3","/usr/sbin/provision/boot.py"])
                
            except Exception as e:
                with open (path + "Error.txt", "a") as file:
                    file.write(str(e))
                log.error("Some error occured during provisoning")

        time.sleep(10)

def compareTime(curHour,curMinute,ON_HOUR,ON_MINUTES,OFF_HOUR,OFF_MINUTES):
    if (ON_HOUR<curHour and curHour<OFF_HOUR):
        return True

    if ((ON_HOUR<curHour) or (ON_HOUR==curHour and ON_MINUTES<=curMinute)):
        if((curHour<OFF_HOUR) or (curHour==OFF_HOUR and curMinute<OFF_MINUTES)):
            return True
            
    return False



def mainLoop():
    global scriptStatus
    log.info("STARTING MAIN LOOP..")
    while True:
        data=None
        with open(path + "ento.conf",'r') as file:
            data=json.load(file)

        if data['device']['TEST_FLAG']=='True':
            duration=int(data['device']['TEST_DURATION'])*60
            testDevice(duration)
        
        ON_HOUR,ON_MINUTES=map(int,data['device']['ON_TIME'].split(":"))
        OFF_HOUR,OFF_MINUTES=map(int,data['device']['OFF_TIME'].split(":"))

        curTime=datetime.now()
        curMinute=curTime.minute
        curHour=curTime.hour

        #Implement the raw logic of testFlag

        if compareTime(curHour,curMinute,ON_HOUR,ON_MINUTES,OFF_HOUR,OFF_MINUTES):
            if not scriptStatus:
                #Start both the services and write the status of the service in the status file
                subprocess.call(["systemctl","restart","cam"])
                subprocess.call(["systemctl","restart","weather"])
                subprocess.call(["systemctl","restart","systeminfo-sd"])
                writeInScriptStatus(True)
                log.info("Cam and upload service started")
        else:
            log.info("Timing not matching")
            if scriptStatus:
                #Stop the service
                subprocess.call(["systemctl","stop","cam"])
                subprocess.call(["systemctl","stop","weather"])
                subprocess.call(["systemctl","stop","systeminfo-sd"])
                writeInScriptStatus(False)
                log.info("Cam and upload service stopped")
    
        time.sleep(5)

if __name__=="__main__":
    log.info("SYNC STARTED..")
    entoDataWriter('device','TEST_FLAG','False')
    writeInScriptStatus(False)
    checkProvisonState()
    subprocess.call(["systemctl","restart","cloud"])
    log.info("Starting JOB reciever..")
    subprocess.call(["systemctl","restart","jobreceiver"])
    mainLoop()