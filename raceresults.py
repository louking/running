#!/usr/bin/python
###########################################################################################
# raceresults  -- retrieve race results from a file
#
#	Date		Author		Reason
#	----		------		------
#       01/07/13        Lou King        Create
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
raceresults  -- retrieve race results from a file
===================================================
'''

# standard
import pdb
import argparse

# pypi

# github

# home grown
import version
from loutilities import textreader
from running import *

# fields is a tuple of dict whose keys are the 'real' information we're interested in
# the value for a particular key contains a tuple with possible header entries which might be used to represent that key
# TODO: get these from a configuration file
fieldxform = {
    'place':['place','pl'],
    'lastname':[['last','name'],'last name','lastname','last'],
    'firstname':[['first','name'],'first name','firstname','first'],
    'name':['name','runner'],
    'gender':['gender','sex','male/female','s'],
    'age':['age','ag'],
    'time':['actual time','time','nettime'],
}

# exceptions for this module.  See __init__.py for package exceptions
class headerError(Exception): pass

########################################################################
class RaceResults():
########################################################################
    '''
    get race results from a file
    
    :params filename: filename from which race results are to be retrieved
    :params distance: distance for race (miles)
    '''
    #----------------------------------------------------------------------
    def __init__(self,filename,distance):
    #----------------------------------------------------------------------
        # open the textreader using the file
        self.file = textreader.TextReader(filename)
        self.filename = filename
        self.distance = distance
        
        # timefactor is based on the first entry's time and distance
        # see self._normalizetime()
        self.timefactor = None
        
        # self.field item value will be of form {'begin':startindex,'end':startindex+length} for easy slicing
        self.field = {}

        # scan to the header line
        self._findhdr()

    #----------------------------------------------------------------------
    def _findhdr(self):
    #----------------------------------------------------------------------
        '''
        find the header in the file
        '''
    
        foundhdr = False
        delimited = self.file.getdelimited()
        fields = fieldxform.keys()
        MINMATCHES = 4
        REQDFIELDS = ['time','gender','age']    # 'name' fields handled separately

        # catch StopIteration, which means header wasn't found in the file
        try:
            # loop for each line until header found
            while True:
                origline = self.file.next()
                fieldsfound = 0
                line = []
                if not delimited:
                    for word in origline.split():
                        line.append(word.lower())
                else:
                    for word in origline:
                        line.append(str(word).lower())  # str() called in case non-string returned in origline
                    
                # loop for each potential self.field in a header
                for fieldndx in range(len(fields)):
                    f = fields[fieldndx]
                    match = fieldxform[f]
                    
                    # loop for each column in this line, trying to find match possiblities
                    for linendx in range(len(line)):
                        # loop for each match possiblity
                        matchfound = False
                        for m in match:
                            # match over the end of the line is no match
                            # m is either a string or a list of strings
                            if type(m) == str:
                                m = [m]         # make single string into list
                            if linendx+len(m)>len(line):
                                continue
                            # if we found the match, remember start and end of match
                            if line[linendx:linendx+len(m)] == m:
                                if f not in self.field: self.field[f] = {}
                                self.field[f]['start'] = linendx
                                self.field[f]['end'] = linendx + len(m)
                                self.field[f]['match'] = m
                                self.field[f]['genfield'] = f   # seems redundant, but [f] index is lost later in self.foundfields
                                fieldsfound += 1
                                matchfound = True
                                break   # match possibility loop
                        
                        # found match for this self.field
                        if matchfound: break
                        
                # here we've gone through each self.field in the line
                # need to match more than MINMATCHES to call it a header line
                if fieldsfound >= MINMATCHES:
                    # special processing for name fields
                    if 'name' not in self.field and ('firstname' in self.field and 'lastname' in self.field):
                        self.splitnames = True
                    elif 'name' in self.field and ('firstname' in self.field and 'lastname' in self.field):
                        self.field.pop('name')  # redundant and wrong
                        self.splitnames = True
                    elif 'name' in self.field and ('lastname' in self.field and 'firstname' not in self.field):
                        namefield = self.field.pop('name')  # assume this was meant to be 'firstname'
                        self.field['firstname'] = namefield
                        self.splitnames = True
                    elif 'name' in self.field and ('lastname' not in self.field and 'firstname' in self.field):
                        raise headerError, '{0}: inconsistent name fields found in header: {1}'.format(self.filename,origline)
                    elif 'name' in self.field:  # not 'lastname' or 'firstname'
                        self.splitnames = False
                    else:                       # insufficient name fields
                        raise headerError, '{0}: no name fields found in header: {1}'.format(self.filename,origline)
                    
                    # verify that all other required fields are present
                    fieldsnotfound = []
                    for f in REQDFIELDS:
                        if f not in self.field:
                            fieldsnotfound.append(f)
                    if len(fieldsnotfound) != 0:
                        raise headerError, '{0}: could not find fields {1} in header {2}'.format(self.filename,fieldsnotfound,origline)
                        
                    # sort found fields by order found within the line
                    foundfields_dec = [(self.field[f]['start'],self.field[f]) for f in self.field]
                    foundfields_dec.sort()
                    self.foundfields = [ff[1] for ff in foundfields_dec] # get rid of sorting decorator
                        
                    # here we have decided it is a header line
                    # if the file is not delimited, we have to find where these fields start
                    # and tell self.file where the self.field breaks are
                    # assume multi self.field matches are separated by single space
                    if not delimited:
                        # sort found fields by 'start' linendx (self.field number within line)
                        # loop through characters in original line, skipping over spaces within matched fields, to determine
                        # where delimiters should be
                        delimiters = []
                        thischar = 0
                        foundfields_iter = iter(self.foundfields)
                        thisfield = next(foundfields_iter)
                        while True:
                            # scan past the white space
                            while thischar < len(origline) and origline[thischar] == ' ': thischar += 1
                            
                            # we're done looking if we're at the end of the line
                            if thischar == len(origline): break
                            
                            # found a word, remember where it was
                            delimiters.append(thischar)
                            
                            # look for the next match of known header fields
                            matchfound = False
                            if thisfield is not None:
                                # if a match, might be multiple words.  Probably ok to assume single space between them
                                fullmatch = ' '.join(thisfield['match'])
                                if origline[thischar:thischar+len(fullmatch)].lower() == fullmatch:
                                    thischar += len(fullmatch)
                                    matchfound = True
                                    try:
                                        thisfield = next(foundfields_iter)
                                    except StopIteration:
                                        thisfield = None
                            
                            # if found a match, thischar is already updated.  Otherwise, scan past this word
                            if not matchfound:
                                while thischar < len(origline) and origline[thischar] != ' ': thischar += 1
                            
                            # we're done looking if we're at the end of the line
                            if thischar == len(origline): break
                        
                        # set up delimiters in the file reader
                        self.file.setdelimiter(delimiters)
                                    
                    break

            # header fields are in foundfields
            # need to figure out the indeces for data which correspond to the foundfields
            self.fieldhdrs = []
            self.fieldcols = []
            skipped = 0
            for f in self.foundfields:
                self.fieldhdrs.append(f['genfield'])
                currcol = f['start'] - skipped
                self.fieldcols.append(currcol)
                skipped += len(f['match']) - 1  # if matched multiple columns, need to skip some
                
        # not good to come here
        except StopIteration:
            raise headerError, '{0}: header not found'.format(self.filename)
        
    #----------------------------------------------------------------------
    def _normalizetime(self,time,distance):
    #----------------------------------------------------------------------
        '''
        normalize the time field, based on distance
        
        :param time: time field from original file
        :param distance: distance of the race, for normalizedtimetype analysis
        
        :rtype: float time (seconds)
        '''
        
        # if string, assume hh:mm:ss or mm:ss or ss
        if type(time) in [str,unicode]:
            timefields = time.split(':')
            tottime = 0.0
            for f in timefields:
                tottime = tottime*60 + float(f)
    
        # if float or int, assume it came from excel, and is in days
        elif type(time) in [float,int]:
            tottime = time * (24*60*60.0)
        
        # it is possible that excel times have been put in as hh:mm accidentally
        # use timefactor to adjust this, based on the time of the first runner, and the distance
        # assume 6mm +/- 50%.  if the time doesn't fit in this range, divide by 60
        # if time still doesn't fit, ask for help (raise exception)
        if not self.timefactor:
            timeestimate = distance * 6.0 * 60  # 6 minute mile
            self.timefactor = 1.0
            if tottime > timeestimate * 1.5:
                self.timefactor = 1/60.0
            if tottime*self.timefactor < timeestimate * 0.5 or tottime*self.timefactor > timeestimate * 1.5:
                raise parameterError, '{0}: invalid time detected - {1} ({2} secs) for {3} mile race'.format(self.filename,time,tottime,distance)
            
        tottime *= self.timefactor
        return tottime
    
    #----------------------------------------------------------------------
    def next(self):
    #----------------------------------------------------------------------
        '''
        return dict with generic headers and associated data from file
        '''
        
        # get next raw line from the file
        # TODO: skip lines which empty text or otherwise invalid lines
        textfound = False
        while not textfound:
            rawline = self.file.next()
            textfound = True    # hope for the best
            
            # pick columns which are associated with generic headers
            filteredline = [rawline[i] for i in range(len(rawline)) if i in self.fieldcols]
            
            # create dict association, similar to csv.DictReader
            result = dict(zip(self.fieldhdrs,filteredline))
            
            # special processing for age - normalize to integer
            if 'age' in result and result['age'] is not None:
                try:
                    result['age'] = int(result['age'])
                except ValueError:
                    textfound = False
                    continue
                
            # special processing for place - normalize to integer
            if 'place' in result and result['place'] is not None:
                try:
                    result['place'] = int(result['place'])
                except ValueError:
                    textfound = False
                    continue
                
            # special processing if name is split, to combine first, last names
            if self.splitnames:
                first = result.pop('firstname')
                last = result.pop('lastname')
                result['name'] = ' '.join([first,last])
                
            # look for some obvious errors in name
            if result['name'] is None or result['name'][0] in '=-/!':
                textfound = False
                continue
            
            # TODO: add normalization for gender
            
            # add normalization for race time (e.g., convert hours to minutes if misuse of excel)
            result['time'] = self._normalizetime(result['time'],self.distance)
        
        # and return result
        return result
    
#----------------------------------------------------------------------
def main(): # TODO: Update this for testing
#----------------------------------------------------------------------
    pass
    
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()