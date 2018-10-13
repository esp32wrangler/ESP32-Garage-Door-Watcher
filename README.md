# ESP32-Garage-Door-Watcher
ESP32-based gadget to check the garage door and send notifications, over wifi, to a smartphone or table if the door is left open. It is using the IFTTT Webhook and notification mechanism to deliver the phone notifications.

What does it do?
A reed switch is used to detect when the door is open, and if it remains open, the script sends a notification after 10 minutes, and an additional notification after 100 minutes. The script keeps the ESP32 in deep sleep as much as possible, and uses the Pin-wake and Timer-wake features to wake up the board for the briefest time to track the garage door state and send the notifications. (Unfortunately the ESP8266's deep sleep feature is much more cumbersome to use, so this script cannot be used on an ESP8266 without significant modifications and additional external wiring).

What do you need? 
- ESP32 board (I'm using a Lolin D32 v1.0, but presumably any other ESP32 should work )
- Micropython image (I tested on v1.9.4) installed on your ESP32 board (many boards come with micropython factory-installed)
- A reed switch (I used a common $1, normally open window sensor kit - the kind that pops up if you search for "reed switch window sensor") 

Setup:
- Attach one lead of the reed switch to the ESP32's GND, and the other lead to a RTC-connected GPIO PIN (I used Pin 2)
- If you don't have an IFTTT account, open one, and create a Webhook that looks something like this: "If Maker Event "garage", then Send a rich notification from the IFTTT app" message: "Garage message: {{Value1}}"
- Find your Webhooks unique ID, by going to https://ifttt.com/maker_webhooks, clicking on "Settings" and then looking at the string that shows up as https://maker.ifttt.com/use/[ID].
- Download the IFTTT app to your smart phone or tablet, and log in with the same user name and password that you used to create the Webhooks notification.
- Set the configuration parameters toward the beginning of main.py (Wifi username and password, Pin number, IFTTT unique ID.
- If you want to change the notification schedule, you can modify the line "notification_delays= [10*60, 100*60]  " (first notification is after 10 minutes, second is after 100 minutes. You can add more notification timings, or change the existing ones
- Upload the main.py with your configuration options to the board, and reset the board. Verify that things work correctly by observing the trace messages in the terminal when you get the magnet closer or further away from the reed relay, and also checking the notifications on your phone.
- Find a place on your garage door railing where you can attach the reed switch, and a corresponding spot on the door to attach the magnet in a way that they come as close as possible when the door is closed (within half an inch should work, and if in doubt you can just add a stick a few more small neodymium disk or cube magnets onto the original magnet, to make the field stronger and the gap smaller).

Special cases:
- If the wifi is not available, the script tries to send the notification every 10 minutes for an hour, and after that it self-resets the board (just in case it is an issue with the wifi stack of the device).
- If you need to modify the main.py, first connect the board to your PC, then connect to the COM port with Putty or another terminal software, press the reset button on the board, and within 10 seconds press ctrl-c in the terminal. When the script detects a cold start or external reset, it will keep the ESP32 awake for 10 seconds to be able to stop the script. Since the script only wakes the ESP32 from deep sleep for brief moments, it is not possible to interrupt the script during normal operation. 

Potential optimizations:
- I didn't put too much emphasis on absolutely optimized power usage, as my unit is running on wall power. But there are a few simple changes that should get you to the point when you can run the device from a battery pack for months or even years:
  - This site claims that a Firebeetle ESP32 board uses significantly less power in deep sleep: https://www.instructables.com/id/ESP32-Deep-Sleep-Tutorial/
  - Instead of using the internal pull-up resistor to bring Pin 2 high, it would be more power efficient to use a 100k, or even maybe a 1 MOhm external resistor. This would reduce the current passing through the reed relay
  - Using a normally closed reed switch would be even more efficient




