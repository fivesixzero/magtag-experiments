import board
import ssl
import socketpool
import wifi
import time
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import neopixel
from digitalio import DigitalInOut, Direction, Pull
import keypad
from analogio import AnalogIn
import json
import re
import terminalio
import displayio
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle
from adafruit_progressbar.progressbar import HorizontalProgressBar

from bulb import Bulb

## Buttons (GPIO15, GPIO14, GPIO12, GPIO11)

button_pins = (
    board.BUTTON_A,
    board.BUTTON_B,
    board.BUTTON_C,
    board.BUTTON_D
)

buttons = keypad.Keys(button_pins, value_when_pressed=False, pull=True)

def retrieve_key_events(keys: keypad.Keys):
    new_events = True
    key_events = []
    while new_events:
        event = keys.events.get()
        if event:
            key_events.append(event)
        else:
            new_events = False
    return key_events

## Battery Management/Voltage Monitor (ADC1 CH8/GPIO9)

batt_monitor = AnalogIn(board.BATTERY)

def battery_status():
    """Return the voltage of the battery"""
    return (batt_monitor.value / 65535.0) * 3.3 * 2
    
## Neopixels (GPIO1, enable/power is GPIO21)

neopixels = neopixel.NeoPixel(board.NEOPIXEL, 4, brightness=0.03)

## Load Secrets

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

## WIFI

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

## MQTT

### Tasmota MQTT Helpers
def topic_breakdown(topic_string):
    topic_expression = "([^/]*)/([^/]*)/([^/]*)"
    topic_re = re.search(topic_expression, topic_string)
    topic = {}
    topic['topic'] = topic
    topic['prefix'] = topic_re.group(1)
    topic['device'] = topic_re.group(2)
    topic['op'] = topic_re.group(3)
    return topic

### Callbacks
def subscribe(mqtt_client, userdata, topic, granted_qos):
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def unsubscribe(mqtt_client, userdata, topic, pid):
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))

def publish(mqtt_client, userdata, topic, pid):
    topic_data = topic_breakdown(topic)
    if topic_data['prefix'] == 'cmnd':
        print("cmnd: {} -> Op: {}".format(topic_data['device'], topic_data['op']))
    else:
        print("Published to {0} with PID {1}".format(topic, pid))

pool = socketpool.SocketPool(wifi.radio)

### Build and configure client
mqtt_client = MQTT.MQTT(
    broker=secrets["mqtt_broker"],
    port=secrets["mqtt_port"],
    username=secrets["mqtt_user"],
    password=secrets["mqtt_password"],
    socket_pool=pool,
    client_id=secrets["mqtt_client_id"],
    ssl_context=ssl.create_default_context()
)

mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish

mqtt_client.connect()
## end MQTT

## Tasmota Device Control
### Define Bulb Names
bulbnames = secrets['bulbs']

### Define Topics for Bulbs
wild_tele = "tele/{}/+"
wild_cmnd = "cmnd/{}/+"
wild_stat = "stat/{}/+"

### Define Commands for Bulbs
cmnd_power = "cmnd/{}/POWER"
cmnd_dimmer = "cmnd/{}/Dimmer"
cmnd_ct = "cmnd/{}/CT"
cmnd_color = "cmnd/{}/Color"
cmnd_status = "cmnd/{}/STATUS"

### Define bulb objects for state tracking along with topics to subscribe to
bulbs = {}
mqtt_topics = []
for bulbname in bulbnames:
    bulbs[bulbname] = Bulb(bulbname)
    mqtt_topics.append(wild_stat.format(bulbname))

### Subscribe to topics for bulbs
for topic in mqtt_topics:
    mqtt_client.subscribe(topic)

### Set up handlers for incoming messages to keep up with bulb statuses
def message(mqtt_client, topic, message):
    topic_data = topic_breakdown(topic)
    if topic_data["prefix"] == "stat":
        bulbname = topic_data["device"]
        if topic_data["op"] == "STATUS11":
            payload = json.loads(message)["StatusSTS"]
            bulbs[bulbname].set_status(payload['POWER'], payload['Dimmer'], payload['CT'], payload['Color'])
            print("MQTT Result: {}".format(bulbs[bulbname]))
        if topic_data["op"] == "RESULT":
            payload = json.loads(message)
            if "POWER" in payload.keys():
                bulbs[bulbname].power = payload["POWER"]
            if "Dimmer" in payload.keys():
                bulbs[bulbname].dimmer = payload["Dimmer"]
            if "CT" in payload.keys():
                bulbs[bulbname].ct = payload["CT"]
            if "Color" in payload.keys():
                bulbs[bulbname].color = payload["Color"]
            print("MQTT Result: {}".format(bulbs[bulbname]))

mqtt_client.on_message = message

## Perform initial state retrieval
print("Initial data retrieval starting")
## Request status info for all bulbs for initial state
for bulb in bulbs:
    mqtt_client.publish(cmnd_status.format(bulb), '11')
    mqtt_client.loop(0.5)
mqtt_client.loop(0.5)
time.sleep(1)
mqtt_client.loop(0.5)
print("Initial data retrieval is complete")

## Display Setup
display = board.DISPLAY
font = terminalio.FONT

def display_refresh():
  time.sleep(display.time_to_refresh)
  try:
    display.refresh()
    while display.busy:
      pass
  except RuntimeError:
    print("Display refresh too soon, waiting before trying again")
    time.sleep(2)
    display.refresh()
    while display.busy:
      pass

## Build Display
### Basics
splash = displayio.Group()
display.show(splash)
### Background and Dividing Lines
bg_bitmap = displayio.Bitmap(display.width, display.height, 2)
bg_palette = displayio.Palette(2)
bg_palette[0] = 0xFFFFFF
bg_palette[1] = 0x000000
bg_sprite = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette, x=0, y=0)
### Title Bar Line
for x in range(0,display.width):
  bg_bitmap[x, 14] = 1
  bg_bitmap[x, display.height - 14] = 1
splash.append(bg_sprite)
### Title/Info Text
title_label = label.Label(
  font, text="Tasmota Bulb MQTT Controller", color=0x000000,
  anchor_point=(0.5, 0.0), anchored_position=(display.width/2, -1)
)
splash.append(title_label)
### Status Line
#### Status Text
status_center = label.Label(
  font, text=" "*20, color=0x000000,
  anchor_point=(0.5, 1.0), anchored_position=(display.width/2, display.height)
)
splash.append(status_center)
#### Status Time
status_right = label.Label(
  font, text=" "*10, color=0x000000,
  anchor_point=(1.0, 1.0), anchored_position=(display.width-1, display.height)
)
splash.append(status_right)
#### Status Server IP
status_left = label.Label(
  font, text=" "*10, color=0x000000,
  anchor_point=(0.0, 1.0), anchored_position=(1, display.height)
)
splash.append(status_left)
### Device Information
device_indicators = {}
device_labels = {}
device_bars = {}
device_line_y_start = 22
device_line_y_sep = 14
device_indicator_x = 7
device_text_x = 67
line = 0
#### Add Device Lines
for name in bulbnames:
  line += 1
  y_position = device_line_y_start
  if line > 1:
    y_position += device_line_y_sep * (line - 1)
  ## Device On/Off Indiciator
  device_indicator = Circle(device_indicator_x, y_position, 5, fill=None, outline=0x000000)
  splash.append(device_indicator)
  device_indicators[name] = device_indicator
  ## Device Text Label
  device_label = label.Label(
    font, text=name, color=0x000000, 
    anchor_point=(0.0, 0.5), anchored_position=(device_text_x, y_position)
  )
  splash.append(device_label)
  device_labels[name] = device_label
  ## Device Brightness Bars
  device_bar = HorizontalProgressBar(
    (15, y_position-5),
    (50, 10),
    bar_color=0x777777,
    outline_color=0x000000,
    fill_color=0xFFFFFF,
    value=5
  )
  splash.append(device_bar)
  device_bars[name] = device_bar
#### End per-device bar setup
## End Display Setup
## Set initial display conditions
for bulbname in bulbnames:
    ## Set indicator for bulb power
    if bulbs[bulbname].power == 'ON':
        device_indicators[bulbname].fill = True
    elif bulbs[bulbname].power == 'OFF':
        device_indicators[bulbname].fill = None
    else:
        device_indicators[bulbname].fill = None
    ## Set indicator for bulb dimming
    dimmer = int(bulbs[bulbname].dimmer)
    if dimmer > 99:
        dimmer = 99
    device_bars[bulbname].value = dimmer
## Refresh display before loop
status_right.text = "Batt: {}v".format(str(battery_status()))
display_refresh()

## Primary Program Loop
print("Starting loop")
button_timer = 0
while True:

    try:
        mqtt_client.loop(0.1)
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        mqtt_client.reconnect()
        continue

    should_change_anything = False
    should_toggle = False
    should_turn_on = False
    should_turn_off = False
    should_just_refresh_display = False
    new_key_events = retrieve_key_events(buttons)
    if len(new_key_events) > 0:
        print("new key events: {}".format(len(new_key_events)))
        for e in new_key_events:
            print("event: {}".format(e))
            if e.pressed and not should_change_anything:
                if e.key_number is 0:
                    should_toggle = True
                elif e.key_number is 1:
                    should_just_refresh_display = True
                elif e.key_number is 2:
                    should_turn_on = True
                elif e.key_number is 3:
                    should_turn_off = True
        should_change_anything = True
        print("events handled: toggle: {}, turn_on: {}, turn_off: {}, just_refresh: {}".format(should_toggle, should_turn_on, should_turn_off, should_just_refresh_display))
    
    # print("timer: {}".format(button_timer))
    if button_timer > 0:
        button_timer -= 1
        if button_timer == 0:
            print("Buttons: Ready for next button input")
            neopixels[0] = (0,0,0)
    else:
        if should_change_anything:
            if should_toggle:
                for bulbname in bulbnames:
                    new_dimmer = int(bulbs[bulbname].dimmer) - 25
                    if new_dimmer <= 10:
                        new_dimmer = 10
                    mqtt_client.publish(cmnd_power.format(bulbname), 'TOGGLE')
                    mqtt_client.loop(0.1)
                mqtt_client.loop(0.1)
                time.sleep(0.1)
                mqtt_client.loop(0.1)
                button_timer = 8
            if should_just_refresh_display:
                print("Battery Status: {}".format(battery_status()))
                mqtt_client.loop(1)
                button_timer = 3
            if should_turn_on:
                mqtt_client.loop(1)
                for bulbname in bulbnames:
                    new_dimmer = int(bulbs[bulbname].dimmer) - 25
                    if new_dimmer <= 10:
                        new_dimmer = 10
                    mqtt_client.publish(cmnd_dimmer.format(bulbname), str(new_dimmer))
                    time.sleep(0.2)
                    mqtt_client.loop(1)
                time.sleep(0.2)
                mqtt_client.loop(1)
                button_timer = 5
            if should_turn_off:
                mqtt_client.loop(1)
                for bulbname in bulbnames:
                    new_dimmer = int(bulbs[bulbname].dimmer) + 25
                    if new_dimmer > 99:
                        new_dimmer = 99
                    mqtt_client.publish(cmnd_dimmer.format(bulbname), str(new_dimmer))
                    time.sleep(0.2)
                    mqtt_client.loop(1)
                time.sleep(0.2)
                mqtt_client.loop(1)
                button_timer = 5
            neopixels[0] = (255,0,0)
            time.sleep(1)
            mqtt_client.loop(0.5)
            for bulbname in bulbnames:
                ## Set indicator for bulb power
                if bulbs[bulbname].power == 'ON':
                    device_indicators[bulbname].fill = True
                elif bulbs[bulbname].power == 'OFF':
                    device_indicators[bulbname].fill = None
                ## Set indicator for bulb dimming
                device_bars[bulbname].value = int(bulbs[bulbname].dimmer)
            status_right.text = str(battery_status())
            display_refresh()

    time.sleep(0.01)