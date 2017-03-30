"""Fake the realtime delivery of archived Level II products
"""

import datetime
import pytz
import glob
import os
import time
import sys

NEXRAD = sys.argv[1]
if len(NEXRAD) != 4:
    print("ERROR NEXRAD should be 4 char")
    sys.exit()
MYDIR = sys.argv[2]

orig0 = datetime.datetime(2014, 6, 30, 15, 40)
orig0 = orig0.replace(tzinfo=pytz.timezone("UTC"))
orig1 = orig0.replace(hour=19, minute=20)

workshop0 = datetime.datetime(2017, 3, 30, 18, 40)
workshop0 = workshop0.replace(tzinfo=pytz.timezone("UTC"))
workshop1 = workshop0.replace(hour=20, minute=30)

speedup = ((orig1 - orig0).total_seconds() /
           (workshop1 - workshop0).total_seconds())
print 'Overall Speedup is %.4f' % (speedup,)


def warp(radts):
    """ Convert the LSR Time to our workshop time, of some sort"""
    return workshop0 + datetime.timedelta(
                seconds=((radts - orig0).total_seconds() / speedup))


def doit(fp, ts):
    cmd = "../l2munger %s %s %s" % (NEXRAD, ts.strftime("%Y/%m/%d %H:%M:%S"),
                                    fp)
    os.system(cmd)
    fp = "%s%s" % (NEXRAD, ts.strftime("%Y%m%d_%H%M%S"))
    os.system("compress %s" % (fp,))
    os.rename("%s.Z" % (fp,), "../../htdocs/l2data/%s/%s.Z" % (NEXRAD, fp))
    os.chdir("../../htdocs/l2data/%s/" % (NEXRAD,))
    os.system("ls -l %s* | awk '{print $5 \" \" $9}' > dir.list" % (NEXRAD,))
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
        print(("Use: %s->%s Fake: %s Left: %s"
               ) % (fn, ts.strftime("%Y%m%d%H%M"),
                    fakets.strftime("%Y-%m-%d %H:%M"),
                    left))
        utcnow = datetime.datetime.utcnow()
        utcnow = utcnow.replace(tzinfo=pytz.timezone("UTC"))
        if fakets > utcnow:
            secs = int((fakets - utcnow).seconds)
            print 'Sleeping for %s seconds' % (secs,)
            time.sleep(secs)
        left -= 1
        doit(fn, fakets)


if __name__ == '__main__':
    main()
