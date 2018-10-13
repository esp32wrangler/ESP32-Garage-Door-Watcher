import socket
import time
import utime
import machine
import os
from machine import Pin
from machine import Timer
import network

s = socket.socket()

#configuration
CONFIG_IFTTT_KEY='MY_IFTTT_WEBHOOD_UID'
CONFIG_WLAN_SSID='SSID_OF_MY_WLAN'
CONFIG_WLAN_PASSWORD='PASSWORD_OF_MY_WLAN'
CONFIG_SENSOR_PIN=2
notification_delays= [10*60, 100*60] 

wlan = network.WLAN(network.STA_IF)

def do_connect(ssid=CONFIG_WLAN_SSID, password=CONFIG_WLAN_PASSWORD):
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(ssid, password)
        for attempt in range (20):
          if wlan.isconnected():
            break
          utime.sleep(1)
        if not wlan.isconnected():
          print ('failed to connect')
          return False
    
    print('network config:', wlan.ifconfig())
    return True  

#Function obtained from https://fullyloadedgeek.com/tag/micropython/ 
#Simple function that handles sending a get request and printing the response
def http_get(site, port, reference, val1, val2, val3):
	address = socket.getaddrinfo(site, port)[0][-1]
	print('Connecting to ', site, '(', address, '):', port)
	s = socket.socket()
	
	s.connect(address)
	
	message = 'GET ' + reference + '?value1=' + str(val1) + '&value2=' + str(val2) + '&value3=' + str(val3) + ' HTTP/1.1\r\nHost: ' + site + '\r\n\r\n'
	print('Sending: ', message)
	s.send(message)
	print(s.recv(500))
	s.close()
  
  
def tinyurlencode(val):
  val=str(val)
  val=val.replace(' ', '%20')
  val=val.replace(':', '%3a')
  return val
  
#Simple function to handle sending the IFTTT get request to trigger an event
def ifttt_message(event, val1, val2, val3):
  do_connect()
  val1=tinyurlencode(val1)
  val2=tinyurlencode(val2)
  val3=tinyurlencode(val3)
  http_get('maker.ifttt.com', 80, '/trigger/' + event + '/with/key/'+ CONFIG_IFTTT_KEY, val1, val2, val3)
 
 
# If an external pull up resistor is used, the Pin.PULL_UP argument is not necessary. Note however, that once set, the pull_up will stay in effect until the next reset
sensor = Pin(CONFIG_SENSOR_PIN, Pin.IN, Pin.PULL_UP) 

door_last_open_time = utime.time()
door_open = (sensor.value() == 1)
current_notification_state = 0
connection_failure_count = 0


def save_and_sleep(pin_trigger, sleep_duration):
  global door_last_open_time, current_notification_state, door_open, connection_failure_count
  saved_data = ','.join( (str(door_last_open_time), str(current_notification_state), str(door_open), str(connection_failure_count)) )
  machine.RTC().memory(saved_data)
  
  sensor.irq(trigger = pin_trigger, wake = machine.DEEPSLEEP)
  # safety sleep to allow debugging
  #machine.sleep(3)
  
  machine.deepsleep(sleep_duration*1000)



if (machine.reset_cause()==machine.DEEPSLEEP_RESET):
  saved_data=machine.RTC().memory()
  print ("woken with data")
  print(saved_data)
  
  split_data = saved_data.split(b',')
 
  if (len(split_data) == 4):
    print ("restoring data", split_data)
    door_last_open_time = int(split_data[0])
    current_notification_state=int(split_data[1])
    #door_open = split_data[2] == b'True'
    connection_failure_count = int(split_data[3])
  if (machine.wake_reason() == machine.PIN_WAKE):
    if (sensor.value() == 1):
      print ("woke and realized the door was open")
      door_last_open_time = utime.time()
      current_notification_state = 0
      door_open=True
      connection_failure_count = 0
      sleepytime = notification_delays[current_notification_state]- (time.time()-door_last_open_time)
      print ("sleeping for %d seconds waiting for first notification" % sleepytime)
      save_and_sleep(machine.Pin.WAKE_LOW, sleepytime)
    else:
      door_open = False
      print ("woke and realized the door was closed, went to sleep")
      save_and_sleep(machine.Pin.WAKE_HIGH, 0)
  
  if(machine.wake_reason() == machine.TIMER_WAKE):
    if (door_open):
      if (connection_failure_count > 6):
        machine.reset()
      if (time.time()-door_last_open_time > notification_delays[current_notification_state]):
        if (do_connect() == False):
          connection_failure_count += 1
          print ("failed to connect, sleeping for 10m")
          save_and_sleep(machine.Pin.WAKE_LOW, 600) 
        ifttt_message('garage', 
        "Garage has been open for: %d minutes" % (notification_delays[current_notification_state]/60),
        '', '')
        current_notification_state += 1
        if (current_notification_state >= len(notification_delays)):
          print ("too many warnings, going to sleep forever", time.time())
          save_and_sleep(machine.Pin.WAKE_LOW, 0)
      
      sleepytime = notification_delays[current_notification_state] - (time.time()-door_last_open_time)
      print ("sleeping for another %d seconds waiting for next notification" % sleepytime)
      save_and_sleep(machine.Pin.WAKE_LOW, sleepytime)
    if(door_closed):
      print ("something funky happened, woke up with the door closed, going back to sleep")
      door_last_open_time = utime.time()
      save_and_sleep(machine.Pin.WAKE_HIGH, 0)
  
else:
  print ("waiting 10 seconds to let you modify main.py, press CTRL-C to exit script")
  utime.sleep(10)
  if (door_open):
    sleepytime = notification_delays[current_notification_state] - (time.time()-door_last_open_time)
    print ("after a clean start sleeping for %d seconds waiting for first notification" % sleepytime)
    save_and_sleep(machine.Pin.WAKE_LOW, sleepytime)
  else:
    print ("after a clean start sleeping soundly with the door closed")
    save_and_sleep(machine.Pin.WAKE_HIGH, 0)
