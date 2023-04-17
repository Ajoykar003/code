


#!/usr/bin/env python3

from base64 import b64encode
import paho.mqtt.client as mqtt
import datetime as dt
import subprocess
import cv2
import random
import json
import sys
import socket
import ast
import time
import os
import csv
import threading
import multiprocessing
from sub import start_subscribe
from pub import start_publish
from publish_weather_data import start_publish_weather_data
from publish_count import start_publish_count
from imageUpload import image_upload_manager
from verification import start_verification
import logging as log

# Systemd notifier class
if sys.version_info < (3,):
    def _b(x):
        return x
else:
    import codecs
    def _b(x):
	    return codecs.latin_1_encode(x)[0]

class SystemdNotifier:
    """This class holds a connection to the systemd notification socket
    and can be used to send messages to systemd using its notify method."""

    def __init__(self, debug=False):
        """Instantiate a new notifier object. This will initiate a connection
        to the systemd notification socket.
        Normally this method silently ignores exceptions (for example, if the
        systemd notification socket is not available) to allow applications to
        function on non-systemd based systems. However, setting debug=True will
        cause this method to raise any exceptions generated to the caller, to
        aid in debugging.
        """
        self.debug = debug
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            addr = os.getenv('NOTIFY_SOCKET')
            if addr[0] == '@':
                addr = '\0' + addr[1:]
            self.socket.connect(addr)
        except Exception:
            self.socket = None
            if self.debug:
                raise

    def notify(self, state):
        """Send a notification to systemd. state is a string; see
        the man page of sd_notify (http://www.freedesktop.org/software/systemd/man/sd_notify.html)
        for a description of the allowable values.
        Normally this method silently ignores exceptions (for example, if the
        systemd notification socket is not available) to allow applications to
        function on non-systemd based systems. However, setting debug=True will
        cause this method to raise any exceptions generated to the caller, to
        aid in debugging."""
        try:
            self.socket.sendall(_b(state))
        except Exception:
            if self.debug:
                raise

# AWS Setup
log.basicConfig(filename='/var/tmp/cloud.log', filemode='w', level=log.INFO, format='[%(asctime)s]- %(message)s', datefmt='%d-%m-%Y %I:%M:%S %p')
with open(f"/etc/entomologist/ento.conf",'r') as file:
        data=json.load(file)
n = None

DEVICE_SERIAL_ID = data["device"]["SERIAL_ID"]
provisionstatus=data["device"]["PROVISION_STATUS"]


MQTT_BROKER = data["device"]["ENDPOINT_URL"]
PORT = 8883
MQTT_KEEP_INTERVAL = 44
rootCA = '/etc/entomologist/cert/AmazonRootCA1.pem'
cert = '/etc/entomologist/cert/certificate.pem.crt'
privateKey = '/etc/entomologist/cert/private.pem.key'

BUCKET_NAME = "test-entomologist-2"

# Publish Details

PUBLISH_CLIENT_NAME = f'{DEVICE_SERIAL_ID}_Publish_Client'
PUBLISH_TOPIC = f'cameraDevice/generateURL/{DEVICE_SERIAL_ID}'
PUBLISH_QoS = 1

# Subscribe Details

SUBSCRIBE_CLIENT_NAME = f'{DEVICE_SERIAL_ID}_Subscribe_Client'
SUBSCRIBE_TOPIC = f'cameraDevice/getURL/{DEVICE_SERIAL_ID}'
SUBSCRIBE_QoS = 0

# Verification Details
VERIFICATION_CLIENT_NAME = f'{DEVICE_SERIAL_ID}_Verification_Client'
VERIFICATION_TOPIC = f'cameraDevice/fileUploaded/{DEVICE_SERIAL_ID}'

# Weather Data Publish Details
WEATHER_DATA_CLIENT_NAME = f'{DEVICE_SERIAL_ID}_WeatherData_Publish_Client'
WEATHER_DATA_TOPIC=f'cameraDevice/get/weatherData/{DEVICE_SERIAL_ID}'


# Count data publish
COUNT_CLIENT_NAME = f'{DEVICE_SERIAL_ID}_COUNT_Publish_Client'
COUNT_TOPIC = f'cameraDevice/get/count/{DEVICE_SERIAL_ID}'


# Buffer Storage Path

BUFFER_IMAGES_PATH = data["device"]["STORAGE_PATH"]
WEATHER_DATA_PATH = data["device"]["WEATHER_STORAGE_PATH"]
COUNT_PATH = data["device"]["COUNT_STORAGE_PATH"]

def generate_payload(filesList):



        payload = {
                "device-serialID":DEVICE_SERIAL_ID,
                "bucket-name":BUCKET_NAME,
                "files": filesList
        }

        return json.dumps(payload)

def signed_url_file_exist():
        log.info("Checking for signed URL json file exist")
        while "signedUrls.json" not in os.listdir():
                time.sleep(2)
        log.info("Signed Url file exist")
        return True


def video_upload_manager(filesList):

        batchSize = len(filesList)

        log.info("Generating for payload")
        publishPayload = generate_payload(filesList)
        log.info("Payload generated for upload")

        # Create start_subscribe and start_publish as two processes by implementing mulitprocessess.
        p1 = threading.Thread(target = start_subscribe, args = [
                MQTT_BROKER,
                PORT,
                MQTT_KEEP_INTERVAL,
                SUBSCRIBE_CLIENT_NAME,
                SUBSCRIBE_TOPIC,
                SUBSCRIBE_QoS,
                rootCA,
                cert,
                privateKey])

        p2 = threading.Thread(target = start_publish, args =[
                MQTT_BROKER,
                PORT,
                MQTT_KEEP_INTERVAL,
                PUBLISH_CLIENT_NAME,
                PUBLISH_TOPIC,
                PUBLISH_QoS,
                publishPayload,
                rootCA,
                cert,
                privateKey])
        p1.start()
        log.info("Start Subscribe process started")
        p2.start()
        log.info("Start Publish process started")
        p1.join()
        p2.join()
        log.info("Subscribe and publish process finished")

        # Create a better implementation once the signedUrls.json file has been created.
        if signed_url_file_exist():

                p3 = threading.Thread(target = start_verification, args = [
                MQTT_BROKER,
                PORT,
                MQTT_KEEP_INTERVAL,
                VERIFICATION_CLIENT_NAME,
                VERIFICATION_TOPIC,
                SUBSCRIBE_QoS,
                batchSize,
                rootCA,
                cert,
                privateKey])

                p4 = threading.Thread(target = image_upload_manager)

                p3.start()
                log.info("Start Verification process started")
                p4.start()
                log.info("Image Upload manager process started")
                p3.join()
                p4.join()
                log.info("Image Upload manager and verification process finished")

                os.remove('signedUrls.json')

def weather_data_upload_manager(dataList):

        for weather_data_file in dataList:
                weather_payload = { "data" : []}
                with open(WEATHER_DATA_PATH + weather_data_file, newline='') as data:
                        reader = csv.DictReader(data)
                        for row in reader:
                                weather_payload["data"].append(row)
                weather_payload = json.dumps(weather_payload)
                start_publish_weather_data(
                MQTT_BROKER,
                PORT,
                MQTT_KEEP_INTERVAL,
                WEATHER_DATA_CLIENT_NAME,
                WEATHER_DATA_TOPIC,
                PUBLISH_QoS,
                weather_payload,
                rootCA,
                cert,
                privateKey,
                weather_data_file)


        ############### count data start

def count_upload_manager(dataList):

        for count_file in dataList:
                count_payload = { "insect_count" : []}
                with open(COUNT_PATH + count_file, newline='') as data:
                        reader = csv.DictReader(data)
                        for row in reader:
                                count_payload["insect_count"].append(row)
                count_payload = json.dumps(count_payload)

                print(count_file)
                start_publish_count(
                MQTT_BROKER,
                PORT,
                MQTT_KEEP_INTERVAL,
                COUNT_CLIENT_NAME,
                COUNT_TOPIC,
                PUBLISH_QoS,
                count_payload,
                rootCA,
                cert,
                privateKey,
                count_file)



        ############# count data end



def video_upload_process():
	while len(os.listdir(BUFFER_IMAGES_PATH)):
              filesList = os.listdir(BUFFER_IMAGES_PATH)[:10]
              n.notify("WATCHDOG=1")
              log.info("Calling video upload manager..")
              video_upload_manager(filesList)
              log.info("Video Upload manager successfully executed..")


def weather_data_upload_process():
        while len(os.listdir(WEATHER_DATA_PATH)):
                n.notify("WATCHDOG=2")
                log.info("Calling weather data upload manager..")
                dataList = os.listdir(WEATHER_DATA_PATH)[:10]
                weather_data_upload_manager(dataList)
                log.info("Weather Data upload manager successfully executed..")


#################### Count upload start

def count_upload_process():
        while len(os.listdir(COUNT_PATH)):
                n.notify("WATCHDOG=3")
                log.info("Calling count data upload manager..")
                dataList = os.listdir(COUNT_PATH)[:10]

                count_upload_manager(dataList)
                log.info("Count Data upload manager successfully executed..")

#################



def main():
    log.info("Cloud Main started..")
    global n
    n = SystemdNotifier()
    while True:
        if provisionstatus=="True":
                video_process = multiprocessing.Process(target = video_upload_process)
                weather_process =  multiprocessing.Process(target = weather_data_upload_process)
                count_process =  multiprocessing.Process(target = count_upload_process)

                weather_process.start()
                count_process.start()
                video_process.start()
                
                weather_process.join()
                count_process.join()
                video_process.join()

                log.info("-"*50)
                time.sleep(1)
        else:
                log.info("I m running but provison status is False")
                time.sleep(10)
main()
