"""Pull what's available on an online Google Spreadsheet into our local DB"""
import datetime

import psycopg2
import pytz
from pyiem.util import exponential_backoff, utc
import pyiem.cscap_utils as util

# First mesh point
ARCHIVE_T0 = utc(2017, 11, 18, 21, 20)
RT_T0 = utc(2022, 3, 31, 18, 58)
# Second mesh point
ARCHIVE_T1 = utc(2017, 11, 18, 23, 17)
RT_T1 = RT_T0 + datetime.timedelta(minutes=90)
SPEEDUP = (ARCHIVE_T1 - ARCHIVE_T0).seconds / float((RT_T1 - RT_T0).seconds)
print(f"Speedup is {SPEEDUP:.2f}")

SHEET = "1_0OV8ecFk1IJIjqFlt5-OBi7khSOD6gccxqUPRbs9gg"
LKP = {
    "HAIL": "H",
    "TORNADO": "T",
    "TSTM WND GST": "G",
    "WIND": "G",
    "TSTM WND DMG": "D",
    "NON-TSTM WND DMG": "O",
    "NON-TSTM WND GST": "N",
    "FUNNEL CLOUD": "C",
    "HEAVY RAIN": "R",
    "FLASH FLOOD": "F",
    "FLOOD": "F",
    "WALL CLOUD": "X",
    "LIGHTNING": "L",
}


def convtime(val):
    """Convert time"""
    try:
        return datetime.datetime.strptime(val, "%m/%d/%Y %H:%M:%S")
    except ValueError:
        return datetime.datetime.strptime(val, "%Y-%m-%d %H:%M")


def main():
    """Go Main Go"""
    mydb = psycopg2.connect("dbname=nwa")
    mcursor = mydb.cursor()
    mcursor.execute("DELETE from lsrs where date(valid) = '2022-03-31'")
    print(f"Deleted {mcursor.rowcount} rows")

    # Get me a client, stat
    config = util.get_config()
    sheets = util.get_sheetsclient(config, "workshop")
    f = sheets.spreadsheets().get(spreadsheetId=SHEET, includeGridData=True)
    j = exponential_backoff(f.execute)

    inserts = 0
    grid = j["sheets"][0]["data"][0]
    cols = [a.get("formattedValue", "") for a in grid["rowData"][0]["values"]]
    for row in grid["rowData"][1:]:
        vals = [a.get("formattedValue") for a in row["values"]]
        data = dict(zip(cols, vals))
        if data.get("Type") is None:
            print()
            continue
        # ts = convtime(data["Obs Time (UTC)"])
        # ts = ts.replace(tzinfo=pytz.UTC)
        # offset = (ts - ARCHIVE_T0).total_seconds() / SPEEDUP
        # valid = RT_T0 + datetime.timedelta(seconds=offset)
        # print(f"{valid:%Y-%m-%d %H:%M}")
        valid = convtime(data["Workshop UTC"]).replace(tzinfo=pytz.UTC)
        display_valid = convtime(data["Workshop Reveal UTC"]).replace(
            tzinfo=pytz.UTC
        )
        # ts = ts.replace(tzinfo=pytz.UTC)
        # if data["Workshop Reveal UTC"] is None:
        #   revealts = ts
        # else:
        #    revealts = convtime(data["Workshop Reveal UTC"])
        #    revealts = revealts.replace(tzinfo=pytz.UTC)
        # if ts != revealts:
        #    print(
        #        ("  Entry has reveal delta of %s minutes")
        #        % ((revealts - ts).total_seconds() / 60.0,)
        #    )
        sql = """
        INSERT into lsrs (valid, display_valid, type, magnitude, city, source,
        remark, typetext, geom, wfo) values (%s, %s, %s, %s, %s, %s,
        %s, %s, 'SRID=4326;POINT(%s %s)', 'DMX')"""
        args = (
            valid,
            display_valid,
            LKP[data["Type"]],
            0 if data["Magnitude"] == "None" else data["Magnitude"],
            data["Workshop City"],
            data["Source"],
            data["Remark"],
            data["Type"],
            float(data["LON"]),
            float(data["LAT"]),
        )
        mcursor.execute(sql, args)
        inserts += 1

    mcursor.close()
    mydb.commit()
    print(f"Inserted {inserts} new entries!")
    print("ALERT: Consider running assign_lsr_wfo.py to get WFO right in DB")


if __name__ == "__main__":
    main()
