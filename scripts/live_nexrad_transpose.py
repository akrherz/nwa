"""Fake the realtime delivery of near realtime data!"""
import os
import sys
import time

# third party
import requests

REAL_NEXRAD = sys.argv[1]
FAKE_NEXRAD = sys.argv[2]
if len(REAL_NEXRAD) != 4 or len(FAKE_NEXRAD) != 4:
    print("ERROR NEXRAD should be 4 char")
    sys.exit()

os.chdir(f"../htdocs/level2/{FAKE_NEXRAD}")


def loop():
    """Go Main Go"""
    baseurl = (
        f"https://mesonet-nexrad.agron.iastate.edu/level2/raw/{REAL_NEXRAD}/"
    )
    req = requests.get(f"{baseurl}dir.list")
    if req.status_code != 200:
        raise Exception(f"Reponse status_code of {req.status_code}")
    lines = req.text.strip().split("\n")
    # Look at the last 5 lines skipping the last one
    for line in lines[-6:]:
        sz, fn = line.strip().split()
        newfn = fn.replace(REAL_NEXRAD, FAKE_NEXRAD)
        if os.path.isfile(newfn) and os.stat(newfn).st_size >= int(sz):
            continue
        print(f"Fetching {fn} of size {sz}")
        req = requests.get(f"{baseurl}{fn}")
        with open(newfn, "wb") as fh:
            fh.write(req.content)
        os.system(
            f"ls -ln {FAKE_NEXRAD}* | awk '{{print $5 \" \" $9}}' > dir.list"
        )


if __name__ == "__main__":
    while True:
        try:
            loop()
        except Exception as exp:
            print("FAIL!")
            print(exp)
        time.sleep(30)
