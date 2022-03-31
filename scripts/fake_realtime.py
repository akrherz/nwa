"""Fake the realtime delivery of archived Level II products."""
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
orig1 = orig0 + datetime.timedelta(minutes=117)

workshop0 = datetime.datetime(2022, 3, 31, 18, 58).replace(tzinfo=pytz.UTC)
workshop1 = workshop0 + datetime.timedelta(minutes=90)

speedup = (orig1 - orig0).total_seconds() / (
    workshop1 - workshop0
).total_seconds()
print(f"Overall Speedup is {speedup:.4f}")


def warp(radts):
    """Convert the LSR Time to our workshop time, of some sort"""
    return workshop0 + datetime.timedelta(
        seconds=((radts - orig0).total_seconds() / speedup)
    )


def doit(fp, ts):
    """Do some work please"""
    cmd = f"../l2munger {NEXRAD} {ts:%Y/%m/%d %H:%M:%S} {speedup:.0f} {fp}"
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    proc.stdout.read()
    fp = f"{NEXRAD}{ts:%Y%m%d_%H%M%S}"
    os.system(f"compress {fp}")
    os.rename(f"{fp}.Z", f"../../htdocs/level2/{NEXRAD}/{fp}.Z")
    os.chdir(f"../../htdocs/level2/{NEXRAD}/")
    # prevent brittle string splitting.
    os.system(f"ls -ln {NEXRAD}* | awk '{{print $5 \" \" $9}}' > dir.list")
    os.chdir(f"../../../scripts/{MYDIR}")


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
        desc = f"{fn}->{ts:%Y%m%d%H%M} {fakets:%Y-%m-%d %H:%M}"
        progress.set_description(desc)
        utcnow = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        if fakets > utcnow:
            secs = int((fakets - utcnow).seconds)
            time.sleep(secs)
        left -= 1
        doit(fn, fakets)


if __name__ == "__main__":
    main()
