#!/usr/bin/python
# ##########################################################################################
#	parseresults.py  -- parse run from garmin training center
#
#	Date		Author		Reason
#	----		------		------
#	03/27/11	Lou King	Create
#
# ##########################################################################################

# standard
import pdb
import optparse
import csv

# ##########################################################################################
def main():
# ##########################################################################################
    usage = "usage: %prog [options] textresults\n\n"
    usage += "where:\n"
    usage += "  <textresults>\ttext file with results\n"
    usage += "  output is put in .csv file with same name\n"

    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-H", "--hdr", dest="hdr", type='int', help="row number for header", default=None)
    parser.set_defaults()
    (options, args) = parser.parse_args()

    textresults = args.pop(0)
    IN = open(textresults, 'r')
    _OUT = open('{0}.csv'.format(textresults),'wb')
    OUT = csv.writer(_OUT)
    
    hdrqueue = []
    foundhdr = False
    
    if options.hdr:
        rowsuntilhdr = options.hdr
        
    # read each row in the input
    for row in IN:
        # if we haven't found the header yet, it's ok to assume we're not processing data yet either
        if not foundhdr:
            hdrqueue.append(row)
            if not options.hdr:
                if len(hdrqueue) > 2: hdrqueue.pop(0)
            else:
                rowsuntilhdr -= 1
            fields = row.split()
            # are we at the row with the heading =='s?
            if (options.hdr and rowsuntilhdr == 0) or (len(fields)>1 and fields[0][0:2] == '=='):
                foundhdr = True
                # make a list of (start,finish) index tuples for the field data
                boundaries = []
                scanndx = 0
                for field in fields:
                    # find start of next field
                    boundaries.append((scanndx,scanndx+len(field)))
                    scanndx += len(field)
                    while scanndx < len(row) and row[scanndx] != '=': scanndx += 1
                # capture header information from previous row
                headers = []
                for boundary in boundaries:
                    hdrrow = hdrqueue[0]
                    headers.append(hdrrow[boundary[0]:boundary[1]].strip())
                OUT.writerow(headers)
            else:
                continue
                    
        # read data rows, splitting according to boundaries
        fields = []
        for boundary in boundaries:
            fields.append(row[boundary[0]:boundary[1]].strip())
        try:
            # if this is ok, then it's a real data row
            placeoa = int(fields[0])
        except ValueError:
            # else continue reading data
            continue
        
        OUT.writerow(fields)
            
    _OUT.close()
    
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()