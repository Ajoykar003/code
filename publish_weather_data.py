#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import json
import csv
import os

with open(f"/etc/entomologist/ento.conf",'r') as file:
	data=json.load(file)
WEATHER_DATA_PATH = data["device"]["WEATHER_STORAGE_PATH"]

TOPIC = None
QoS = None
PAYLOAD = None
WEATHER_FILLE = None


def on_publish(client, userdata, message):
	print("Data Published. Deleting File...\n")
	try:
		os.remove(WEATHER_DATA_PATH + WEATHER_FILLE)
		print(f"{WEATHER_FILLE} Deleted Successfully. Disconnecting from clinet...")
	except Exception as e:
		print(f"{WEATHER_FILLE} could not be deleted. Disconnecting from client...")
		print(e)
	client.disconnect()

def on_connect(client, userdata, flags, rc):
	if rc == 0:
		print("Publish Client Connected")
	else:
		print("Bad connection: Publish Client")


def start_publish_weather_data(broker, port, interval , clientName, topic, qos, payload, rootCA, cert, privateKey, weather_file):

	global TOPIC
	global QoS
	global PAYLOAD
	global WEATHER_FILLE

	TOPIC = topic
	QoS = qos
	PAYLOAD = payload
	WEATHER_FILLE = weather_file

	# AWS Publishing Cient
	pubClient = mqtt.Client(clientName)

	# Setting Certificates
	pubClient.tls_set(rootCA, cert, privateKey)

	# Callback functions
	pubClient.on_connect = on_connect
	pubClient.on_publish = on_publish
	
	# Connecting to broker and publishing payload.
	pubClient.connect(broker, port, interval)
	pubClient.publish(topic, payload, qos)

	pubClient.loop_forever()