#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec 28 21:54:04 2019

@author: sven
"""
import requests
import json

raspi_id = "192.168.178.22"
data = {"devicetype": "raspi_light_control"}
res = requests.post("http://" + raspi_id + "/api", json.dumps(data))
apikey = json.loads(res.text)[0]['success']['username']
print(apikey)