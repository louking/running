#!/usr/bin/python
# ##########################################################################################
#   racewx - determine weather for race day
#
#	Date		Author		Reason
#	----		------		------
#	08/29/12	Lou King	Create
#
# ##########################################################################################
'''
racewx - determine weather for race day
===================================================
'''

# standard
import pdb
import argparse
import datetime
import urllib.request, urllib.parse, urllib.error
import json
import csv
import time
import math
import os.path

# pypi
import pytz # also consider https://pypi.python.org/pypi/gaepytz (tuned for google app engine)
import httplib2

# github
import gpxpy
import gpxpy.geo

# home grown
from . import version
from running import *
from loutilities import timeu
from loutilities import apikey

_ak = apikey.ApiKey('Lou King','running')
try:
    _FORECASTIOKEY = _ak.getkey('forecastio')
except apikey.unknownKey:
    print("'forecastio' key needs to be configured using apikey")
    raise

WXPERIOD = 5*60    # number of seconds between weather assessments
#tgpx = timeu.asctime('%Y-%m-%dT%H:%M:%S%Z')

HTTPTIMEOUT = 5
HTTPTZ = httplib2.Http(timeout=HTTPTIMEOUT)
HTTPWX = httplib2.Http(timeout=HTTPTIMEOUT,disable_ssl_certificate_validation=True)

# dewpoint from http://www.meteo-blog.net/2012-05/dewpoint-calculation-script-in-python/
# dewpoint constants
DPa = 17.271
DPb = 237.7 # degC

# heat index from http://en.wikipedia.org/wiki/Heat_index
# heat index constants
HIc = [None,-42.379,2.04901523,10.14333127,-0.22475541,-6.83783e-3,-5.481717e-2,1.22874e-3,8.5282e-4,-1.99e-6]

#----------------------------------------------------------------------
def dewpoint(temp,humidity):
#----------------------------------------------------------------------
    '''
    approximate dewpoint from temp and relative humidity
    from http://www.meteo-blog.net/2012-05/dewpoint-calculation-script-in-python/
    
    :param temp: temperature (fahrenheit)
    :param humidity: relative humidity (1-100)
    :rtype: dewpoint (fahrenheit)
    '''
    
    tempC = celsius(temp)
    Td = (DPb * gamma(tempC,humidity)) / (DPa - gamma(tempC,humidity))
 
    return fahrenheit(Td)
 
#---------------------------------------------------------------------- 
def gamma(tempC,humidity):
#----------------------------------------------------------------------
    '''
    gamma function for dewpoint calculation
    from http://www.meteo-blog.net/2012-05/dewpoint-calculation-script-in-python/
    
    :param tempC: temperature (celcius)
    :param humidity: relative humidity (1-100)
    '''
 
    g = (DPa * tempC / (DPb + tempC)) + math.log(humidity/100.0)
 
    return g
 
#----------------------------------------------------------------------
def windchill(temp,windspeed):
#----------------------------------------------------------------------
    '''
    wind chill calculation
    from http://en.wikipedia.org/wiki/Wind_chill#North_American_and_UK_wind_chill_index
    
    :param temp: temperature (fahrenheit)
    :param windspeed: wind speed (mph)
    :rtype: windchill (fahrenheit) or None if temp > 50 or windspeed < 3 mph
    '''
    
    if temp <= 50 and windspeed >= 3.0:
        return 35.74 + 0.6215*temp - 35.75*windspeed**0.16 + 0.4275*temp*windspeed**0.16
    else:
        return None

#----------------------------------------------------------------------
def heatindex(temp,humidity):
#----------------------------------------------------------------------
    '''
    heat index calculation
    from http://en.wikipedia.org/wiki/Heat_index#Formula
    
    :param temp: temperature (fahrenheit)
    :param humidity: relative humidity (0-100)
    :rtype: heat index (fahrenheit) or None if temp < 80 or humidity < 40
    '''
    
    if temp >= 80 and humidity >= 40:
        return (HIc[1] + HIc[2]*temp + HIc[3]*humidity + HIc[4]*temp*humidity + HIc[5]*temp**2 
                + HIc[6]*humidity**2 + HIc[7]*temp**2*humidity + HIc[8]*temp*humidity**2 + HIc[9]*temp**2*humidity**2)
    else:
        return None

#----------------------------------------------------------------------
def celsius(temp):
#----------------------------------------------------------------------
    '''
    convert Fahrenheit temp to Celcius
    
    :param temp: temperature in Fahrenheit
    :rtype: temperature in Celcius
    '''
    return (temp - 32) / (9.0/5.0)

#----------------------------------------------------------------------
def fahrenheit(temp):
#----------------------------------------------------------------------
    '''
    convert Celcius temp to Fahrenheit
    
    :param temp: temperature in Celcius
    :rtype: temperature in Fahrenheit
    '''
    return (temp * (9.0/5.0)) + 32

#----------------------------------------------------------------------
def gettzid(lat,lon):
#----------------------------------------------------------------------
    '''
    get time zone name based on lat, lon
    uses google maps api
    
    :param lat: latitude in decimal degrees
    :param lon: longitude in decimal degrees
    '''

    params = {'location':'{lat},{lon}'.format(lat=lat,lon=lon),
              'timestamp':0,
              'sensor':'true'}
    body = urllib.parse.urlencode(params)
    url = 'https://maps.googleapis.com/maps/api/timezone/json?{body}'.format(body=body)
    resp,jsoncontent = HTTPTZ.request(url)

    if resp.status != 200:
        raise accessError('URL response status = {0}'.format(resp.status))
    
    # unmarshall the response content
    content = json.loads(jsoncontent)

    if content['status'] != 'OK':
        raise accessError('URL content status = {0}'.format(content['status']))
    
    return content['timeZoneId']
    
#----------------------------------------------------------------------
def getwx(lat,lon,etime):
#----------------------------------------------------------------------
    '''
    get weather from forecast.io for specified latitude, longitude, time
    
    :param lat: latitude
    :param long: longitude
    :param etime: time in unix format (that is, seconds since midnight GMT on 1 Jan 1970)
    :rtype: weather dict for that location, time, e.g., {u'temperature': 46.59, u'precipType': u'rain', u'humidity': 0.62, u'cloudCover': 0.53, u'summary': u'Mostly Cloudy', u'pressure': 1014.87, u'windSpeed': 8.63, u'visibility': 10, u'time': 1366036200, u'windBearing': 326, u'icon': u'partly-cloudy-day'}
    '''
    
    url = 'http://api.forecast.io/forecast/{apikey}/{lat},{lon},{time}'.format(apikey=_FORECASTIOKEY,lat=lat,lon=lon,time=etime)
    resp,jsoncontent = HTTPWX.request(url)
    
    if resp.status != 200:
        raise accessError('URL response status = {0}'.format(resp.status))
    
    # unmarshall the response content, and return the weather for that time
    content = json.loads(jsoncontent)
    return content['currently']

#----------------------------------------------------------------------
def main():
#----------------------------------------------------------------------

    parser = argparse.ArgumentParser(version='{0} {1}'.format('running',version.__version__))
    parser.add_argument('gpxfile',help='gpx formatted file')
    parser.add_argument('racestarttime',help="time of race start in '%%Y-%%m-%%dT%%H:%%M' format")
    parser.add_argument('-o','--output',help='name of output file (default %(default)s)',default='racewx.csv')
    args = parser.parse_args()

    gpxfile = args.gpxfile
    racestarttime = args.racestarttime
    timrace = timeu.asctime('%Y-%m-%dT%H:%M')
    racestartdt = timrace.asc2dt(racestarttime) # naive
    output = args.output
    
    # get input
    _GPX = open(gpxfile,'r')
    gpx = gpxpy.parse(_GPX)

    # loop through gpx tracks
    wxdata = []
    lasttime = None
    exectime = int(round(time.time()))
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                pepoch = timeu.dt2epoch(point.time)
                if not lasttime or pepoch-lasttime >= WXPERIOD:
                    plon = point.longitude
                    plat = point.latitude
                    if not lasttime:
                        starttime = pepoch
                        tzid = gettzid(plat, plon)
                        tz = pytz.timezone(tzid)
                        racestartlocdt = tz.normalize(tz.localize(racestartdt))
                        racestartepoch = timeu.dt2epoch(racestartlocdt)
                        shift = racestartepoch - starttime
                    targtime = timeu.dt2epoch(point.time)+shift # shift to race time
                    
                    # get weather
                    # temp, dew point, cloud cover, precip intensity
                    # wind speed/bearing: http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.barbs
                    #   (http://matplotlib.1069221.n5.nabble.com/plot-arrows-for-wind-direction-degrees-td13499.html)
                    wx = getwx(plat,plon,targtime)
                    wx['lat'] = plat
                    wx['lon'] = plon
                    wx['dewpoint'] = dewpoint(wx['temperature'],wx['humidity']*100)
                    wx['windchill'] = windchill(wx['temperature'],wx['windSpeed'])
                    wx['heatindex'] = heatindex(wx['temperature'],wx['humidity']*100)
                    wxdata.append(wx)
                    
                    lasttime = pepoch

    # create the file and write header if it doesn't exist
    if not os.path.exists(output):
        writeheader = True
        _WX = open(output,'wb')
    else:
        writeheader = False        
        _WX = open(output,'ab')
        
    heading = ['exectime', 'time', 'lat', 'lon', 'temperature', 'humidity', 'dewpoint', 'windchill', 'heatindex', 'precipType', 'precipProbability', 'precipIntensity', 'windSpeed', 'windBearing', 'cloudCover', 'summary', 'pressure', 'visibility']
    WX = csv.DictWriter(_WX,heading,extrasaction='ignore')
    if writeheader:
        WX.writeheader()
    for wx in wxdata:
        wx['exectime'] = exectime
        WX.writerow(wx)
    _WX.close()

# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

