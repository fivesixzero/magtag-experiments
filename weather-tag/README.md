# weather-tag

Simple MagTag weather fetcher

## Overview

This uses the US National Weather Service API to retrieve basic forecast data and displays it on the MagTag.

## Usage

1. Set up MagTag with Circuitpython 6.x+
2. Copy required CircuitPython libraries to MagTag in `lib` directory
  * `adafruit_magtag`
  * `adafruit_bitmap_font`
  * `adafruit_display_text`
  * `adafruit_io`
  * `adafruit_requests.mpy`
  * `neopixel.mpy`
  * `simpleio.mpy`
3. Edit `secrets.py` in main directory with `ssid` and `password` for wireless network
4. Edit `secrets.py` to include the US NWS Weather Forecast Office and Gridpoint for forecast
  * See https://www.weather.gov/srh/nwsoffices to find the WFO for your location
  * See https://weather-gov.github.io/api/gridpoints for more info on how to find the gridpoint for your location.
5. Copy `code.py` and `secrets.py` to MagTag
6. Watch the magic happen :)