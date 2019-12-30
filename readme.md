# Configure VNC viewer
* Type 'sudo raspi-config'
  + select interface
  + select vnc and enable vnc
* open /root/.vnc/config.d/vncserver-x11 and add at the end of the file
  + Authentication=VncAuth
  + Encryption=AlwaysOff
  + Password=e0fd0472492935da
* restart raspberry
* use 'vncpasswd -service' to change password

# configure GUI
* Type 'sudo raspi-config' somewhere there you can select that
the gui starts automatically on every boot.

# Install deConz and Phoscon
* Download the deConz installer from the Dresden Elektronik website.
* Install the package.
* Connect to the ip address of the raspberry pi using __raspi_ip/pwa/login.html__

# Configure lights
Connect to the raspberry lights configurartion by http://raspy_ip/login.html
Default Username is:
username: delight
password: delight

## Acquire API key
To acquire an api-key sign into lights configuration. Go to settings and unlock the
gateway. Send a post reqest to http://rapi_ip/api with the paramter "devicetype" set.
  import requests
  import json

  raspi_id = "192.168.178.22"
  data = {"devicetype": "raspi_light_control"}
  res = requests.post("http://" + raspi_id + "/api", json.dumps(data)
  apikey = json.loads(res.text)[0]['success']['username']
  print(apikey)

## Turn on lights
  import requests
  import json
  data = json.dumps({"on": True})
  requests.put("http://" + rapi_id + "/api/#apikey#/lights/1/state/", data)

## Start script on startup
1) Copy script to file system
2) sudo crontab -e
3) Add @reboot python3 /home/pi/.../...py &
