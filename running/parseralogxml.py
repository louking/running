# standard
from argparse import ArgumentParser
from csv import DictWriter
from datetime import timedelta

# pypi
from loutilities.xmldict import ConvertXmlToDict

class ParameterError(Exception): pass

def dist2miles(distel):
    dist = float(distel['_text'])
    distunits = distel['unit']
    if distunits == 'mi':
        pass
    elif distunits == 'km':
        dist /= 1.609344
    elif distunits == 'm':
        dist /= 1609.344
    else:
        raise ParameterError(f'unexpected distance unit {distunits}')
    
    return dist

def convertsecs(dur):
    return str(timedelta(seconds = float(dur)))
    
def main():
    parser = ArgumentParser()
    parser.add_argument('-X', '--xmlfile', help='input xml file, from RunningAHEAD export', required=True)
    parser.add_argument('-C', '--csvfile', help='output csv file', required=True)
    args = parser.parse_args()

    fieldnames = 'date,time,type,subtype,dist,duration,equipment,route,temp,notes'.split(',')
    workouts = ConvertXmlToDict(args.xmlfile)
    with open(args.csvfile, 'w', newline='') as oscsvfile:
        csvfile = DictWriter(oscsvfile, fieldnames=fieldnames)
        csvfile.writeheader()
        for wo in workouts['RunningAHEADLog']['EventCollection']['Event']:
            if wo['typeName'] not in ['Run', 'Bike', 'Walk']: continue
            datetime = wo['time']
            datetimesplit = datetime.split('T')
            date = datetimesplit[0]
            time = datetimesplit[1] if len(datetimesplit) == 2 else ''
            time = time[:-1] if time and time[-1] == 'Z' else time
            row = {
                'date':      date,
                'time':      time,
                'type':      wo['typeName'],
                'subtype':   wo['subtypeName'] if 'subtypeName' in wo else '',
                'dist':      dist2miles(wo['Distance']) if 'Distance' in wo else '',
                'duration':  convertsecs(wo['Duration']['seconds']) if 'Duration' in wo else '',
                'equipment': wo['Equipment']['_text'] if 'Equipment' in wo else '',
                'route':     wo['Route']['_text'] if 'Route' in wo else '',
                'temp':      wo['EnvironmentalConditions']['Temperature']['_text'] if 'EnvironmentalConditions' in wo and 'Temperature' in wo['EnvironmentalConditions'] else '',
                'notes':     wo['Notes'] if 'Notes' in wo else '',
            }
            csvfile.writerow(row)
    
if __name__ == "__main__":
    main()