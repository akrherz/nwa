"""Pull what's available on an online Google Spreadsheet into our local DB"""
from __future__ import print_function
import datetime

import psycopg2
import pytz
import pyiem.cscap_utils as util

SHEET = "1tkIttjziC4Ob3Gh9oWXuFs1-sE0CUNfIzpw_vjfSxek"
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
    mcursor.execute(
        """
        DELETE from lsrs where date(valid) = '2019-03-28'
    """
    )
    print("Deleted %s rows" % (mcursor.rowcount,))

    # Get me a client, stat
    config = util.get_config()
    sheets = util.get_sheetsclient(config, "cscap")
    f = sheets.spreadsheets().get(spreadsheetId=SHEET, includeGridData=True)
    j = util.exponential_backoff(f.execute)

    inserts = 0
    grid = j["sheets"][0]["data"][0]
    cols = [a["formattedValue"] for a in grid["rowData"][0]["values"]]
    print(cols)
    for row in grid["rowData"][1:]:
        vals = [a.get("formattedValue") for a in row["values"]]
        data = dict(zip(cols, vals))
        if data["Workshop UTC"] is None:
            continue
        ts = convtime(data["Workshop UTC"])
        ts = ts.replace(tzinfo=pytz.UTC)
        if data["Workshop Reveal UTC"] is None:
            revealts = ts
        else:
            revealts = convtime(data["Workshop Reveal UTC"])
            revealts = revealts.replace(tzinfo=pytz.UTC)
        if ts != revealts:
            print(
                ("  Entry has reveal delta of %s minutes")
                % ((revealts - ts).total_seconds() / 60.0,)
            )
        geo = "SRID=4326;POINT(%s %s)" % (data["LON"], data["LAT"])
        sql = """
        INSERT into lsrs (valid, display_valid, type, magnitude, city, source,
        remark, typetext, geom, wfo) values (%s, %s, %s, %s, %s, %s,
        %s, %s, %s, 'DMX')"""
        args = (
            ts,
            revealts,
            LKP[data["Type"]],
            0 if data["Magnitude"] == "None" else data["Magnitude"],
            data["Workshop City"],
            data["source"],
            data["Remark"],
            data["Type"],
            geo,
        )
        mcursor.execute(sql, args)
        inserts += 1

    mcursor.close()
    mydb.commit()
    print("Inserted %s new entries!" % (inserts,))
    print("ALERT: Consider running assign_lsr_wfo.py to get WFO right in DB")


if __name__ == "__main__":
    main()
