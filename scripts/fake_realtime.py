"""
 Need something to drive the placement of files in a realtime directory

the times would be from 0423Z to 0737Z

3hr14m (194m) in 90m

KSGF20120229_030039_V06
KSGF20120229_085728_V06
"""

import datetime
import pytz
import glob
import os
import time

# First mesh point
ARCHIVE_T0 = datetime.datetime(2012, 4, 15, 0, 0)
ARCHIVE_T0 = ARCHIVE_T0.replace(tzinfo=pytz.timezone("UTC"))
RT_T0 = datetime.datetime(2015, 3, 26, 18, 40)  # 1:40 PM
RT_T0 = RT_T0.replace(tzinfo=pytz.timezone("UTC"))
# Second mesh point
ARCHIVE_T1 = datetime.datetime(2012, 4, 15, 3, 45)
ARCHIVE_T1 = ARCHIVE_T1.replace(tzinfo=pytz.timezone("UTC"))
RT_T1 = RT_T0 + datetime.timedelta(minutes=90)

SPEEDUP = (ARCHIVE_T1 - ARCHIVE_T0).seconds / float((RT_T1 - RT_T0).seconds)
print 'Speedup is %.2f' % (SPEEDUP,)


def doit(fp, ts):
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
        ts = datetime.datetime.strptime(fn[4:19], '%Y%m%d_%H%M%S')
        ts = ts.replace(tzinfo=pytz.timezone("UTC"))
        offset = ((ts - ARCHIVE_T0).days * 86400. +
                  (ts - ARCHIVE_T0).seconds) / SPEEDUP
        fakets = RT_T0 + datetime.timedelta(seconds=offset)
        print "Use: %s TS: %s Left: %s" % (fn,
                                           fakets.strftime("%Y-%m-%d %H:%M"),
                                           left)
        utcnow = datetime.datetime.utcnow()
        utcnow = utcnow.replace(tzinfo=pytz.timezone("UTC"))
        if fakets > utcnow:
            secs = int((fakets - utcnow).seconds)
            print 'Sleeping for %s seconds' % (secs,)
            time.sleep(secs)
        left -= 1
        doit( fn, fakets )

main()
