#!/usr/bin/python
###########################################################################################
# runningaheadparticipants -- class pulls in individual registrations for later processing
#
#       Date            Author          Reason
#       ----            ------          ------
#       04/11/15        Lou King        Create
#
#   Copyright 2015 Lou King
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

# standard
import csv

# home grown

########################################################################
class RunningAheadParticipant():
########################################################################
    '''
    Represents single RunningAHEAD registration

    :param registration: registration record from RunningAHEAD export file
    '''

    # translate selected fields of file header to attributes we want to keep
    'Participant ID,Registration Date,Event Category,Status,Bib,Last Name,First Name,Middle Name,Gender,Age,DOB,Email,Street 1,Street 2,City,State,ZIP Code,Country'

    filehdr = 'Registration Date,Event Category,Status,Bib,Last Name,First Name,Middle Name,Gender,Age,DOB,Email,Street 1,Street 2,City,State,ZIP Code,Country'.split(',')
    participantattr = 'registrationdate,category,status,bib,lname,fname,mname,gender,age,dob,email,street1,street2,city,state,zip,country'.split(',')
    participantxlate = dict(list(zip(filehdr,participantattr)))

    # only repr these fields
    reprattr = 'fname,lname,dob,registrationdate'.split(',')

    #----------------------------------------------------------------------
    def __init__(self,registration):
    #----------------------------------------------------------------------

        for key in self.filehdr:
            if key in self.participantxlate:
                setattr(self,self.participantxlate[key],registration[key])

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------

        reprval = '{}('.format(self.__class__)
        for attr in self.reprattr:
            if attr[0:2] == '__' or attr == 'fields': continue
            reprval += '{}={},'.format(attr,getattr(self,attr))
        reprval = reprval[:-1]  #remove trailing comma
        reprval += ')'
        return reprval



########################################################################
class RunningAheadParticipants():
########################################################################
    '''
    Collect participant data from RunningAHEAD event registration export
    file.

    Provide access functions to gain access to these registration records.

    :param participantfile: participant filename, filehandle or string of file records
    :param overlapfile: debug file to test for overlaps between records
    '''

    #----------------------------------------------------------------------
    def __init__(self,participantfile,overlapfile=None):
    #----------------------------------------------------------------------

        # check for type of participantfile, assume not opened here
        openedhere = False

        # if str, assume this is the filename
        if isinstance(participantfile, str):
            participantfileh = open(participantfile, 'rb')
            openedhere = True

        # if file, reparticipant handle
        elif isinstance(participantfile, file):
            participantfileh = participantfile

        # if list, it works like a handle
        elif isinstance(participantfile, list):
            participantfileh = participantfile

        # otherwise, not handled
        else:
            raise unsupportedFileType

        # input is csv file
        INCSV = csv.DictReader(participantfileh)
        
        # pull in each record in the file
        self.registrations = {}
        for registration in INCSV:
            thisparticipant = RunningAheadParticipant(registration)
            lname = thisparticipant.lname
            fname = thisparticipant.fname
            dob = thisparticipant.dob

            # get list of records associated with each participant, pulling out significant fields
            thisrec = {'lname':lname,'fname':fname,'dob':dob,'fullrec':registration,'RunningAheadParticipant':thisparticipant}
            thisname = (thisparticipant.lname,thisparticipant.fname,thisparticipant.dob)
            self.registrations[thisname] = thisrec

    #----------------------------------------------------------------------
    def allregistrations_iter(self):
    #----------------------------------------------------------------------
        '''
        generator function that yields full record for each registrations
        '''
        for thisregistration in self.registrations:
            yield self.registrations[thisregistration]['RunningAheadParticipant']

    #----------------------------------------------------------------------
    def activeregistrations_iter(self):
    #----------------------------------------------------------------------
        '''
        generator function that yields full record for each registrations
        '''
        for thisregistration in self.registrations:
            if self.registrations[thisregistration]['RunningAheadParticipant'].status == 'Registered':
                yield self.registrations[thisregistration]['RunningAheadParticipant']

