"""Fake the realtime delivery of archived Level II products
"""
from __future__ import print_function

import datetime
import glob
import os
import time
import sys

import pytz

NEXRAD = sys.argv[1]
if len(NEXRAD) != 4:
    print("ERROR NEXRAD should be 4 char")
    sys.exit()
MYDIR = sys.argv[2]

orig0 = datetime.datetime(2017, 7, 10, 1, 0)
orig0 = orig0.replace(tzinfo=pytz.UTC)
orig1 = orig0 + datetime.timedelta(minutes=180)

workshop0 = datetime.datetime(2019, 3, 28, 19, 0)
workshop0 = workshop0.replace(tzinfo=pytz.UTC)
workshop1 = workshop0 + datetime.timedelta(minutes=90)

speedup = (orig1 - orig0).total_seconds() / (
    workshop1 - workshop0
).total_seconds()
print("Overall Speedup is %.4f" % (speedup,))


def warp(radts):
    """ Convert the LSR Time to our workshop time, of some sort"""
    return workshop0 + datetime.timedelta(
        seconds=((radts - orig0).total_seconds() / speedup)
    )


def doit(fp, ts):
    """Do some work please"""
    cmd = ("../l2munger %s %s %.0f %s") % (
        NEXRAD,
        ts.strftime("%Y/%m/%d %H:%M:%S"),
        speedup,
        fp,
    )
    os.system(cmd)
    fp = "%s%s" % (NEXRAD, ts.strftime("%Y%m%d_%H%M%S"))
    os.system("compress %s" % (fp,))
    os.rename("%s.Z" % (fp,), "../../htdocs/l2data/%s/%s.Z" % (NEXRAD, fp))
    os.chdir("../../htdocs/l2data/%s/" % (NEXRAD,))
    os.system("ls -l %s* | awk '{print $5 \" \" $9}' > dir.list" % (NEXRAD,))
    os.chdir("../../../scripts/" + MYDIR)


def main():
    """Go Main Go"""
    # Load Filenames, figure if they should be immediately moved
    os.chdir(MYDIR)
    files = glob.glob("*")
    files.sort()
    left = len(files)
    for fn in files:
        # KTLX20090210_180130_V03
        ts = datetime.datetime.strptime(fn[4:19], "%Y%m%d_%H%M%S")
        ts = ts.replace(tzinfo=pytz.utc)
        fakets = warp(ts)
        print(
            ("Use: %s->%s Fake: %s Left: %s")
            % (
                fn,
                ts.strftime("%Y%m%d%H%M"),
                fakets.strftime("%Y-%m-%d %H:%M"),
                left,
            )
        )
        utcnow = datetime.datetime.utcnow()
        utcnow = utcnow.replace(tzinfo=pytz.UTC)
        if fakets > utcnow:
            secs = int((fakets - utcnow).seconds)
            print("Sleeping for %s seconds" % (secs,))
            time.sleep(secs)
        left -= 1
        doit(fn, fakets)


if __name__ == "__main__":
    main()
