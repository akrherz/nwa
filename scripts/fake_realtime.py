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

# ______________________________________________________________________
# Upstream is sync_google!
orig0 = datetime.datetime(1999, 4, 8, 19, 37)
orig0 = orig0.replace(tzinfo=pytz.timezone("UTC"))
origB = orig0.replace(hour=20, minute=50)
orig1 = orig0.replace(hour=23, minute=16)

workshop0 = datetime.datetime(2016, 3, 31, 18, 10)
workshop0 = workshop0.replace(tzinfo=pytz.timezone("UTC"))
workshopB1 = workshop0.replace(hour=18, minute=40)
workshopB2 = workshop0.replace(hour=18, minute=50)
workshop1 = workshop0.replace(hour=19, minute=50)

speedup = ((orig1 - orig0).total_seconds() /
           (workshop1 - workshop0).total_seconds())
print 'Overall Speedup is %.4f' % (speedup,)
speedup1 = ((origB - orig0).total_seconds() /
            (workshopB1 - workshop0).total_seconds())
print 'Par1    Speedup is %.4f' % (speedup1,)
speedup2 = ((orig1 - origB).total_seconds() /
            (workshop1 - workshopB2).total_seconds())
print 'Part2   Speedup is %.4f' % (speedup2,)


def warp(lsrtime):
    """ Convert the LSR Time to our workshop time, of some sort"""
    base = orig0 if lsrtime < origB else origB
    newbase = workshop0 if lsrtime < origB else workshopB2
    _speedup = speedup1 if lsrtime < origB else speedup2
    return newbase + datetime.timedelta(
                seconds=((lsrtime - base).total_seconds() / _speedup))
# ______________________________________________________________________

MYDIR = "l2data_2016nwa"


def doit(fp, ts):
    cmd = "../l2munger KDMX %s %s" % (ts.strftime("%Y/%m/%d %H:%M:%S"), fp)
    os.system(cmd)
    fp = "KDMX%s" % (ts.strftime("%Y%m%d_%H%M%S"),)
    os.system("compress %s" % (fp,))
    os.rename("%s.Z" % (fp,), "../../htdocs/l2data/KDMX/%s.Z" % (fp,))
    os.chdir("../../htdocs/l2data/KDMX/")
    os.system("ls -l KDMX* | awk '{print $5 \" \" $9}' > dir.list")
    os.chdir("../../../scripts/" + MYDIR)


def main():
    # Load Filenames, figure if they should be immediately moved
    os.chdir(MYDIR)
    files = glob.glob("*")
    files.sort()
    left = len(files)
    for fn in files:
        # KTLX20090210_180130_V03
        ts = datetime.datetime.strptime(fn[4:19], '%Y%m%d_%H%M%S')
        ts = ts.replace(tzinfo=pytz.timezone("UTC"))
        fakets = warp(ts)
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
        doit(fn, fakets)

main()
