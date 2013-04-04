"""
 Need something to drive the placement of files in a realtime directory

the times would be from 0423Z to 0737Z

3hr14m (194m) in 90m

KSGF20120229_030039_V06
KSGF20120229_085728_V06
"""

import mx.DateTime
import glob, os, time

# First mesh point
ARCHIVE_T0 = mx.DateTime.DateTime(2012,2,29,4,4) # was 0423z
RT_T0 = mx.DateTime.DateTime(2013,4,4,19,10) # 2:10 PM
# Second mesh point
ARCHIVE_T1 = mx.DateTime.DateTime(2012,2,29,7,37)
RT_T1 = RT_T0 + mx.DateTime.RelativeDateTime(minutes=90) 

SPEEDUP = (ARCHIVE_T1 - ARCHIVE_T0).minutes / (RT_T1 - RT_T0).minutes
print 'Speedup is %.2f' % (SPEEDUP,)

def doit( fp, ts ):
    cmd = "../l2munger KDMX %s %s" % (ts.strftime("%Y/%m/%d %H:%M:%S"), fp)
    os.system(cmd)
    fp = "KDMX%s" % (ts.strftime("%Y%m%d_%H%M%S"),)
    os.system("compress %s" % (fp,))
    os.rename("%s.Z" % (fp,), "../../htdocs/l2data/KDMX/%s.Z" % (fp,)) 
    os.chdir("../../htdocs/l2data/KDMX/")
    os.system("ls -l KDMX* | awk '{print $5 \" \" $9}' > dir.list")
    os.chdir("../../../scripts/l2data")

def main():
    # Load Filenames, figure if they should be immediately moved
    os.chdir("l2data")
    files = glob.glob("*")
    files.sort()
    left = len(files)
    for fn in files:
        # KTLX20090210_180130_V03
        ts = mx.DateTime.strptime(fn[4:19], '%Y%m%d_%H%M%S')
      
        offset = (ts - ARCHIVE_T0).minutes / SPEEDUP
        fakets = RT_T0 + mx.DateTime.RelativeDateTime(minutes=offset)
        print "Process: %s TS: %s Left: %s" % (fn, 
                                fakets.strftime("%Y-%m-%d %H:%M"), left )
        if fakets > mx.DateTime.gmt():
            secs = int((fakets - mx.DateTime.gmt()).seconds)
            print 'Sleeping for %s seconds' % (secs,)
            time.sleep( int((fakets - mx.DateTime.gmt()).seconds) )
        left -= 1
        doit( fn, fakets )

main()