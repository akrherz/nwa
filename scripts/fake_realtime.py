"""Fake the realtime delivery of archived Level II products."""

import glob
import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone

import click
from tqdm import tqdm


def warp(
    radts: datetime, workshop0: datetime, orig0: datetime, speedup: float
):
    """Convert the LSR Time to our workshop time, of some sort"""
    return workshop0 + timedelta(
        seconds=((radts - orig0).total_seconds() / speedup)
    )


def doit(fp: str, nexrad: str, ts: datetime, speedup: float):
    """Do some work please"""
    cmd = [
        "../l2munger",
        nexrad,
        f"{ts:%Y/%m/%d}",
        f"{ts:%H:%M:%S}",
        f"{speedup:.0f}",
        fp,
    ]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
        proc.stdout.read()
    fp = f"{nexrad}{ts:%Y%m%d_%H%M%S}"
    subprocess.call(["gzip", "-S", ".Z", fp])
    os.rename(f"{fp}.Z", f"../../htdocs/level2/{nexrad}/{fp}.Z")
    cwd = os.getcwd()
    os.chdir(f"../../htdocs/level2/{nexrad}/")
    # prevent brittle string splitting.
    os.system(f"ls -ln {nexrad}* | awk '{{print $5 \" \" $9}}' > dir.list")
    os.chdir(cwd)


@click.command()
@click.option("--nexrad", default="KDMX", help="NEXRAD Site to Fake")
@click.option("--dir", "dirname", required=True, help="Directory to process")
def main(nexrad: str, dirname: str):
    """Go Main Go"""
    cfg = json.load(open("../config/workshop.json"))
    timing = cfg["timing"]
    for key in timing:
        timing[key] = datetime.strptime(
            timing[key], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)

    speedup = (
        timing["archive_end"] - timing["archive_begin"]
    ).total_seconds() / (
        timing["workshop_end"] - timing["workshop_begin"]
    ).total_seconds()
    print(f"Speedup: {speedup:.2f}x")

    # Load Filenames, figure if they should be immediately moved
    os.chdir(dirname)
    files = glob.glob("*")
    files.sort()
    left = len(files)
    progress = tqdm(files)
    for fn in progress:
        # KTLX20090210_180130_V03
        ts = datetime.strptime(fn[4:19], "%Y%m%d_%H%M%S").replace(
            tzinfo=timezone.utc
        )
        fakets = warp(
            ts, timing["workshop_begin"], timing["archive_begin"], speedup
        )
        desc = f"{fn}->{ts:%Y%m%d%H%M} {fakets:%Y-%m-%d %H:%M}"
        progress.set_description(desc)
        utcnow = datetime.now(timezone.utc)
        if fakets > utcnow:
            secs = int((fakets - utcnow).seconds)
            time.sleep(secs)
        left -= 1
        doit(fn, nexrad, fakets, speedup)


if __name__ == "__main__":
    main()
