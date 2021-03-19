"""Fake the realtime delivery of archived Level II products
"""
import subprocess
import datetime
import glob
import os
import time
import sys

from tqdm import tqdm
import pytz

NEXRAD = sys.argv[1]
if len(NEXRAD) != 4:
    print("ERROR NEXRAD should be 4 char")
    sys.exit()
MYDIR = sys.argv[2]

orig0 = datetime.datetime(2017, 11, 18, 21, 20).replace(tzinfo=pytz.UTC)
orig1 = orig0 + datetime.timedelta(minutes=114)

workshop0 = datetime.datetime(2021, 3, 19, 15, 30).replace(tzinfo=pytz.UTC)
workshop1 = workshop0 + datetime.timedelta(minutes=76)

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
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    proc.stdout.read()
    fp = "%s%s" % (NEXRAD, ts.strftime("%Y%m%d_%H%M%S"))
    os.system("compress %s" % (fp,))
    os.rename("%s.Z" % (fp,), "../../htdocs/l2data/%s/%s.Z" % (NEXRAD, fp))
    os.chdir("../../htdocs/l2data/%s/" % (NEXRAD,))
    # prevent brittle string splitting.
    os.system("ls -ln %s* | awk '{print $5 \" \" $9}' > dir.list" % (NEXRAD,))
    os.chdir("../../../scripts/" + MYDIR)


def main():
    """Go Main Go"""
    # Load Filenames, figure if they should be immediately moved
    os.chdir(MYDIR)
    files = glob.glob("*")
    files.sort()
    left = len(files)
    progress = tqdm(files)
    for fn in progress:
        # KTLX20090210_180130_V03
        ts = datetime.datetime.strptime(fn[4:19], "%Y%m%d_%H%M%S")
        ts = ts.replace(tzinfo=pytz.utc)
        fakets = warp(ts)
        desc = "%s->%s %s" % (
            fn,
            ts.strftime("%Y%m%d%H%M"),
            fakets.strftime("%Y-%m-%d %H:%M"),
        )
        progress.set_description(desc)
        utcnow = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        if fakets > utcnow:
            secs = int((fakets - utcnow).seconds)
            time.sleep(secs)
        left -= 1
        doit(fn, fakets)


if __name__ == "__main__":
    main()
