import socket
import time
import utime
import machine
import os
import ntptime
from machine import Pin
from machine import Timer
from machine import RTC

from math import cos, sin, acos as arccos, asin as arcsin, tan as tg, degrees, radians

s = socket.socket()

#configuration
CONFIG_IFTTT_KEY='MY_IFTTT_WEBHOOK_UID'
CONFIG_WLAN_SSID='SSID_OF_MY_WLAN'
CONFIG_WLAN_PASSWORD='PASSWORD_OF_MY_WLAN'
CONFIG_SENSOR_PIN=2
CONFIG_ON_PIN=22
CONFIG_OFF_PIN=23
GEO_LAT=MY_LATITUDE
GEO_LON=MY_LONGITUDE


import network
wlan = network.WLAN(network.STA_IF)

def isLeapYear(year):
  return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0

MONTHS=[31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def getDayNumber(year, month, day):
  cnt = 0
  for yr in range(1900,year):
    if isLeapYear(yr):
      cnt += 366
    else:
      cnt += 365
  for mo in range(1,month):
    cnt += MONTHS[mo-1]
    if mo == 2 and isLeapYear(year):
      cnt += 1
        
  return cnt + day - 1

# based on: http://www.srrb.noaa.gov/highlights/sunrise/calcdetails.html
# https://michelanders.blogspot.com/2010/12/calulating-sunrise-and-sunset-in-python.html
def getSunriseAndSunset(lat, lon, dst, year, month, day):
  localtime = 12.00
  b2 = lat
  b3 = lon
  b4 = dst
  b5 = localtime / 24
  b6 = year
  d30 = getDayNumber(year, month, day)
  e30 = b5
  f30 = d30 + 2415018.5 + e30 - b4 / 24
  g30 = (f30 - 2451545) / 36525
  q30 = 23 + (26 + ((21.448 - g30 * (46.815 + g30 * (0.00059 - g30 * 0.001813)))) / 60) / 60
  r30 = q30 + 0.00256 * cos(radians(125.04 - 1934.136 * g30))
  j30 = 357.52911 + g30 * (35999.05029 - 0.0001537 * g30)
  k30 = 0.016708634 - g30 * (0.000042037 + 0.0000001267 * g30)
  l30 = sin(radians(j30)) * (1.914602 - g30 * (0.004817 + 0.000014 * g30)) + sin(radians(2 * j30)) * (0.019993 - 0.000101 * g30) + sin(radians(3 * j30)) * 0.000289
  i30 = (280.46646 + g30 * (36000.76983 + g30 * 0.0003032)) % 360
  m30 = i30 + l30
  p30 = m30 - 0.00569 - 0.00478 * sin(radians(125.04 - 1934.136 * g30))
  t30 = degrees(arcsin(sin(radians(r30)) * sin(radians(p30))))
  u30 = tg(radians(r30 / 2)) * tg(radians(r30 / 2))
  v30 = 4 * degrees(u30 * sin(2 * radians(i30)) - 2 * k30 * sin(radians(j30)) + 4 * k30 * u30 * sin(radians(j30)) * cos(2 * radians(i30)) - 0.5 * u30 * u30 * sin(4 * radians(i30)) - 1.25 * k30 * k30 * sin(2 * radians(j30)))
  w30 = degrees(arccos(cos(radians(90.833)) / (cos(radians(b2)) * cos(radians(t30))) - tg(radians(b2)) * tg(radians(t30))))
  x30 = (720 - 4 * b3 - v30 + b4 * 60) / 1440
  y30 = (x30 * 1440 - w30 * 4) / 1440
  z30 = (x30 * 1440 + w30 * 4) / 1440
  sunrise = y30 * 24
  sunset = z30 * 24
  return (sunrise, sunset)


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
	
  
import socket

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
 
 
# Init global variables
sensor = Pin(CONFIG_SENSOR_PIN, Pin.IN, Pin.PULL_UP)
light_on_pin = Pin(CONFIG_ON_PIN, Pin.OPEN_DRAIN, value=1)
light_off_pin = Pin(CONFIG_OFF_PIN, Pin.OPEN_DRAIN, value=1)

door_last_open_time = utime.time()
door_open = (sensor.value() == 1)
notification_delays= [10*60, 100*60] 
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

def turn_lights_off ():
  light_off_pin.value(0)
  time.sleep_ms(500)
  light_off_pin.value(1)
  
def turn_lights_on ():
  light_on_pin.value(0)
  time.sleep_ms(500)
  light_on_pin.value(1)

def is_nighttime():
  try:
    do_connect()
    ntptime.settime() # set the rtc datetime from the remote server
  except:
    if (machine.RTC().datetime()[0] >= 2020): # RTC was synchronized since boot
      print ("Warning: NTP failed, falling back to RTC")
    else:
      print ("Error: no clue what the time is, assuming nighttime")
      return True
  current_time=machine.RTC().datetime() # get the date and time in UTC  
  sunrise, sunset = getSunriseAndSunset(GEO_LAT, GEO_LON, 0, current_time[0], current_time[1], current_time[2])
  current_time_in_fraction = current_time[4]+current_time[5]/60.0
  return current_time_in_fraction < sunrise or current_time_in_fraction > sunset
  

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
      
      if (is_nighttime()):
        print ("it is nighttime, turning lights on")
        turn_lights_on()
      else:
        print ("it is the day, don't waste energy")
      
      door_last_open_time = utime.time()
      current_notification_state = 0
      door_open=True
      connection_failure_count = 0
      sleepytime = notification_delays[current_notification_state]- (time.time()-door_last_open_time)
      print ("sleeping for %d seconds waiting for first notification" % sleepytime)
      save_and_sleep(machine.Pin.WAKE_LOW, sleepytime)
    else:
      print ("woke and realized the door was closed, turning lights off")
      turn_lights_off()
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
          print ("too many warnings, going to sleep forever and turning lights off", time.time())
          turn_lights_off()
          save_and_sleep(machine.Pin.WAKE_LOW, 0)
      
      sleepytime = notification_delays[current_notification_state] - (time.time()-door_last_open_time)
      print ("sleeping for another %d seconds waiting for next notification" % sleepytime)
      save_and_sleep(machine.Pin.WAKE_LOW, sleepytime)
    if(door_closed):
      print ("something funky happened, woke up with the door closed, going back to sleep")
      turn_lights_off()
      door_last_open_time = utime.time()
      save_and_sleep(machine.Pin.WAKE_HIGH, 0)
else:
  print ("safety sleep, press CTRL-C to exit")
  utime.sleep(10)
  
  if (door_open):
    print ("clean start with the door open, turning lights on - test feature")
    turn_lights_on()
    sleepytime = notification_delays[current_notification_state] - (time.time()-door_last_open_time)
    print ("after a clean start sleeping for %d seconds waiting for first notification" % sleepytime)
    save_and_sleep(machine.Pin.WAKE_LOW, sleepytime)
  else:
    print ("after a clean start sleeping soundly with the door closed")
    save_and_sleep(machine.Pin.WAKE_HIGH, 0)


#sensor.irq(handler=lambda p:magnet_irq(), trigger=(Pin.IRQ_FALLING | Pin.IRQ_RISING), wake=machine.DEEPSLEEP)

  
#ifttt_message('node_bootup', wlan.ifconfig()[0], '8266', '?')  

#machine.Pin.WAKE_LOW





