# Configure VNC viewer
* Type 'sudo raspi-config'
  + select interface
  + select vnc and enable vnc
* open /root/.vnc/config.d/vncserver-x11 and add at the end of the file
  + Authentication=VncAuth
  + Encryption=AlwaysOff
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
  
  raspi_id = ##IP Address Raspberry##
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

## Create new user to run the script
1) Create user
   sudo useradd -M lmanager
2) make user a non log in user.
   sudo usermod -L lmanager
3) Copy script to user's home directory and start crontab as user
   sudo crontab -u lmanager -e

## Configure firewall to block external commands send to deconz
  #!/bin/sh
  
  iptables -F
  iptables -X
  
  iptables -P INPUT ACCEPT
  iptables -P OUTPUT ACCEPT
  iptables -P FORWARD ACCEPT
  
  iptables -A INPUT -i lo -j ACCEPT
  iptables -A OUTPUT -o lo -j ACCEPT
  
  iptables -A INPUT -p tcp --dport 80 -j DROP
  iptables -A OUTPUT -p tcp --sport 80 -j DROP

Make iptables permanent
  sudo apt  iptables-persistent

Save iptables rules
  iptables-save > /etc/iptables/rules.v4
  ip6tables-save > /etc/iptables/rules.v6

Activate iptables
  sudo service netfilter-persisten start

## Save power
### Disable HDMI
Add
  /usr/bin/tvservice -o
to ''/etc/rc.local'' to disable HDMI on boot.

### Disable LED
Add
  dtparam=act_led_trigger=none
  dtparam=act_led_activelow=on
to ''/boot/config.txt''

## Disable Audio
Can also be done in ''/boot/config.txt''.
