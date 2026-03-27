"""Pull what's available on an online Google Spreadsheet into our local DB"""

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import isudatateam.cscap_utils as util
import psycopg2

SHEET = "1kVg4SXL3ZNRwpjqcm47Fdr6-ndHj2xqGUplIG7k7jnE"
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
        return datetime.strptime(val, "%m/%d/%Y %H:%M:%S")
    except ValueError:
        return datetime.strptime(val, "%Y-%m-%d %H:%M")


def main():
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

    mydb = psycopg2.connect("dbname=nwa")
    mcursor = mydb.cursor()
    mcursor.execute("DELETE from lsrs where date(valid) = '2026-03-25'")
    print(f"Deleted {mcursor.rowcount} rows")

    # Get me a client, stat
    config = util.get_config()
    sheets = util.get_sheetsclient(config, "workshop")
    sheet = (
        sheets.spreadsheets()
        .get(spreadsheetId=SHEET, includeGridData=True)
        .execute()
    )

    inserts = 0
    grid = sheet["sheets"][0]["data"][0]
    cols = [a.get("formattedValue", "") for a in grid["rowData"][0]["values"]]
    for row in grid["rowData"][1:]:
        vals = [a.get("formattedValue") for a in row["values"]]
        data = dict(zip(cols, vals, strict=False))
        if data.get("Type") is None:
            print()
            continue
        # if data["Workshop UTC"].strip() != "":
        #    print(f"{convtime(data['Workshop UTC']):%Y-%m-%d %H:%M}")
        #    continue
        valid = convtime(data["Obs Time (UTC)"]).replace(tzinfo=timezone.utc)
        offset = (valid - timing["archive_begin"]).total_seconds() / speedup
        valid = timing["workshop_begin"] + timedelta(seconds=offset)
        print(f"{valid:%Y-%m-%d %H:%M}")
        # continue
        valid = convtime(data["Workshop UTC"]).replace(tzinfo=timezone.utc)
        # display_valid = convtime(data["Workshop Reveal UTC"]).replace(
        #    tzinfo=ZoneInfo("UTC")
        # )
        # ts = ts.replace(tzinfo=ZoneInfo("UTC"))
        if data["Workshop Reveal UTC"] is None:
            revealts = valid
        else:
            revealts = convtime(data["Workshop Reveal UTC"])
            revealts = revealts.replace(tzinfo=ZoneInfo("UTC"))
        # if ts != revealts:
        #    print(
        #        ("  Entry has reveal delta of %s minutes")
        #        % ((revealts - ts).total_seconds() / 60.0,)
        #    )
        sql = """
        INSERT into lsrs (valid, display_valid, type, magnitude, city, source,
        remark, typetext, geom, wfo) values (%s, %s, %s, %s, %s, %s,
        %s, %s, ST_Point(%s, %s, 4326), 'DMX')"""
        args = (
            valid,
            revealts,
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
