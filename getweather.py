#!/usr/bin/python
###########################################################################################
# getweather - get specified weather information from forecast.io
#
#	Date		Author		Reason
#	----		------		------
#       04/10/13        Lou King        Create
#
#   Copyright 2013 Lou King
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###########################################################################################
'''
getweather - get specified weather information from forecast.io
==============================================================================

'''
# standard
import pdb
import argparse
import textwrap
import csv

# pypi
import pytz 

# github

# other

# home grown
import version
from loutilities import timeu

#----------------------------------------------------------------------
def main():
#----------------------------------------------------------------------

    description = 'Get specified weather information from forecast.io'
    epilog = textwrap.dedent('''\
        paramsfile contains the following
        
            [getweather]
            starttime = <starttime>
            wxpoints = {"dist":[deltat,deltat,...],
                "dist":[deltat,deltat,...],
                ...
                }
        
        where:
            <starttime>\tstarting time for collection, in 'yyyy-mm-dd HH:MM' format (no quotes, local timezone)
            <dist>\tdistance in miles from the first gpx point
            <deltat>\ttime in seconds from <starttime> for weather collection
            
        outfile is a csv file, with a header row, containing the following fields - see https://developer.forecast.io/docs/v2 Data Points for details
        
            exectime\ttime script was executed (Unix time format)
            time\ttime forecast is predicting for (Unix time format)
            lat
            lon
            temperature
            humidity
            dewpoint\tcalculated from temperature, humidity
            windchill\tcalculated from temperature, windSpeed
            heatindex\tcalculated from temperature, humidity
            precipType
            precipProbability
            precipIntensity
            windSpeed
            windBearing
            cloudCover
            summary
            pressure
            visibility
        ''')
    parser = argparse.ArgumentParser(
        prog='getweather.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=description,
        epilog=epilog,
        version='{0} {1}'.format('running',version.__version__))
    parser.add_argument('gpxfile',help='gpx file containing course')
    parser.add_argument('paramsfile',help='file containing parameters')
    parser.add_argument('outfile',help='csv file containing output from queries')
    parser.add_argument('-a','--apikey',help='API key to access forecast.io')
    args = parser.parse_args()
    
# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

