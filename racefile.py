#!/usr/bin/python
###########################################################################################
#   racefile - load file containing race information
#
#   Date        Author      Reason
#   ----        ------      ------
#   01/21/13    Lou King    Create
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
fsrcresult - determine results for FSRC racesracefile - load file containing race information
==========================================================
'''

# standard
import pdb
import argparse
import collections

# pypi
import xlrd

# github

# other

# home grown
from fsrc import *
from loutilities import timeu

tYmd = timeu.asctime('%Y-%m-%d')
DEBUG = None

########################################################################
class RaceFile():
########################################################################
    '''
    RaceFile object 
    
    :params filename: excel file from which races are to be retrieved
    '''
    #----------------------------------------------------------------------
    def __init__(self,filename):
    #----------------------------------------------------------------------

        # get the worksheet from the workbook
        workbook = xlrd.open_workbook(filename)
        races_sheet = workbook.sheet_by_name('races')
        series_sheet = workbook.sheet_by_name('series')
        workbook.release_resources()    # sheet is already loaded so we can save memory

        # collect series information
        # header row is first row
        # series header has at least series,age grade,overall,divisions
        self.series = collections.OrderedDict()
        serieshdr = series_sheet.row_values(0)
        nrows = series_sheet.nrows
        for rowndx in range(1,nrows):
            thisrow_list = series_sheet.row_values(rowndx)
            thisrow_dict = dict(zip(serieshdr,thisrow_list))
            thisseries = thisrow_dict.pop('series')
            # any attribute which starts with 'Y' or 'y' is True, otherwise False
            for attr in thisrow_dict:
                if thisrow_dict[attr] and thisrow_dict[attr].lower()[0] == 'y':
                    thisrow_dict[attr] = True
                else:
                    thisrow_dict[attr] = False
            self.series[thisseries] = thisrow_dict
        
        # collect race information by race, also collecting series attributes
        # header row is first row
        # races header has at least date,time,race,series,result file
        self.races = []
        raceshdr = races_sheet.row_values(0)
        nrows = races_sheet.nrows
        for rowndx in range(1,nrows):
            thisrow_list = races_sheet.row_values(rowndx)
            thisrow_dict = dict(zip(raceshdr,thisrow_list))
            thisrow_dict['racenum'] = rowndx
            ## general series is always included, please others as indicated in file, delimited by ','
            thisrace_series = ['general']
            addlseries = thisrow_dict['series'].split(',')
            if len(addlseries) > 0 and addlseries[0]:   # may only contain null string. if so skip append
                thisrace_series += addlseries
            # TODO: {plan is to loop for each series, then use races which are included in the series 
            #       so no real use for series attributes retrievable from race
            #thisrow_dict['seriesattr'] = {}
            #for s in thisrace_series:
            #    thisrow_dict['seriesattr'][s] = series[s]
            # TODO: }
            thisrow_dict['inseries'] = thisrace_series
            # convert date to ascii from excel.  If ValueError, leave date as it was
            try:
                thisrow_dict['date'] = tYmd.dt2asc(timeu.excel2dt(thisrow_dict['date']))
            except TypeError:
                pass
            self.races.append(thisrow_dict)
            
