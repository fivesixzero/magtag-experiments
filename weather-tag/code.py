from adafruit_magtag.magtag import MagTag
import time
import terminalio
import ipaddress
import json
from secrets import secrets

WX_URL_BASE = 'https://api.weather.gov'
WX_URL_ENDPOINT = '/gridpoints/{}/{}/forecast'

wx_url = WX_URL_BASE + WX_URL_ENDPOINT.format(secrets['nws_wfo'], secrets['nws_gridpoint'])
print("WX URL:", wx_url)

magtag = MagTag()
print("MagTag IP address is", magtag.network._wifi.ip_address)

magtag.add_text(
    text_font=terminalio.FONT,
    text_position=(3,(magtag.graphics.display.height // 2) - 1,),
    text_scale=1,
    line_spacing=1.1
)

def get_wx_text(response_string):
    wx_raw = json.loads(response_string)

    wx_time_raw = wx_raw['properties']['generatedAt']

    wx = [
        wx_raw['properties']['periods'][0],
        wx_raw['properties']['periods'][1],
        wx_raw['properties']['periods'][2],
        wx_raw['properties']['periods'][3],
        wx_raw['properties']['periods'][4],
        wx_raw['properties']['periods'][5],
        wx_raw['properties']['periods'][6]
    ]

    wx_text = 'Upcoming Forecast {:>30}'.format(wx_time_raw)

    for wx_line in wx:
        wx_text += '\n'
        wx_text += '{:16} {:3}f {}'.format(wx_line['name'], wx_line['temperature'], wx_line['shortForecast'])
    
    return wx_text

def retrieve_wx_data():
    print("Retrieving forecast from NWS API for wfo: {}, gridpoint: {}".format(secrets['nws_wfo'], secrets['nws_gridpoint']))
    response_string = magtag.network.fetch_data(wx_url)
    print("NWS API call complete")

    wx_text = get_wx_text(response_string)

    return wx_text

def display_update(display_text):
    if (magtag.display.time_to_refresh > 0):
        print("Sleeping to allow for display refresh")
        time.sleep(magtag.display.time_to_refresh + 0.1)
        print("Sleep for display refresh is complete")

    magtag.set_text(display_text)

print("Initial data retrieve in progress")
wx_text = retrieve_wx_data()
print("Initial data retrieve complete")

display_update(wx_text)

magtag.peripherals.neopixels.brightness = 0.01
buttons = magtag.peripherals.buttons
button_colors = ((255, 0, 0), (255, 150, 0), (0, 255, 255), (180, 0, 255))
timestamp = time.monotonic()

while True:
    for i, b in enumerate(buttons):
        if not b.value:
            button_string = chr((ord("A") + i))
            print("Button {} pressed".format(button_string))
            magtag.peripherals.neopixel_disable = False
            magtag.peripherals.neopixels.fill(button_colors[i])
            if (button_string == 'D'):
                display_update(retrieve_wx_data())
            break
    else:
        magtag.peripherals.neopixel_disable = True
    time.sleep(0.01)