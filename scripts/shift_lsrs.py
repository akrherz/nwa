"""Need to shift LSRs in space and time"""

import math
from datetime import timedelta, timezone

from psycopg.rows import dict_row
from pyiem import util
from pyiem.network import Table as NetworkTable
from pyproj import Transformer

T_4326_2163 = Transformer.from_proj(4326, 2163, always_xy=True)
T_2163_4326 = Transformer.from_proj(2163, 4326, always_xy=True)
nt = NetworkTable("NEXRAD")
POSTGIS = util.get_dbconn("postgis")
pcursor = POSTGIS.cursor(row_factory=dict_row)
NWA = util.get_dbconn("nwa", host="localhost", user="mesonet")
ncursor = NWA.cursor(row_factory=dict_row)

# First mesh point
ARCHIVE_T0 = util.utc(2020, 4, 12, 19, 0)
RT_T0 = util.utc(2024, 3, 27, 19, 0)
# Second mesh point
ARCHIVE_T1 = util.utc(2020, 4, 12, 21, 30)
RT_T1 = RT_T0 + timedelta(minutes=90)

SPEEDUP = (ARCHIVE_T1 - ARCHIVE_T0).seconds / float((RT_T1 - RT_T0).seconds)
print(f"Speedup is {SPEEDUP:.2f}")

# Site NEXRAD
REAL88D = "DGX"
FAKE88D = "DMX"
NEXRAD_LAT = nt.sts[REAL88D]["lat"]
NEXRAD_LON = nt.sts[REAL88D]["lon"]
FAKE_NEXRAD_LAT = nt.sts[FAKE88D]["lat"]
FAKE_NEXRAD_LON = nt.sts[FAKE88D]["lon"]


def getdir(u, v):
    """Convert to a direction."""
    if v == 0:
        v = 0.000000001
    dd = math.atan(u / v)
    ddir = (dd * 180.00) / math.pi

    if u > 0 and v > 0:  # First Quad
        ddir = 180 + ddir
    elif u > 0 and v < 0:  # Second Quad
        ddir = 360 + ddir
    # elif u < 0 and v < 0:  # Third Quad
    #    ddir = ddir
    elif u < 0 and v > 0:  # Fourth Quad
        ddir = 180 + ddir

    return int(math.fabs(ddir))


def workflow(csvfp):
    """Go!"""
    ncursor.execute(
        "DELETE from lsrs WHERE valid > %s and valid < %s",
        (
            RT_T0 - timedelta(minutes=300),
            RT_T1 + timedelta(minutes=300),
        ),
    )
    print(f"Removed {ncursor.rowcount} rows from nwa lsr table")

    # Get Fake coords in 2163
    radx, rady = T_4326_2163.transform(FAKE_NEXRAD_LON, FAKE_NEXRAD_LAT)

    sts = ARCHIVE_T0 - timedelta(minutes=300)
    ets = ARCHIVE_T1 + timedelta(minutes=300)
    # Get all LSRs within 230m of the nexrad
    pcursor.execute(
        """SELECT distinct *, ST_astext(geom) as tgeom,
        ST_x( ST_transform( geom, 2163) ) -
            ST_x( ST_transform(
                ST_POINT(%s, %s, 4326), 2163)) as offset_x,
        ST_y( ST_transform( geom, 2163) ) -
            ST_y( ST_transform(
                ST_POINT(%s, %s, 4326), 2163)) as offset_y
        from lsrs WHERE valid BETWEEN %s and %s
        and ST_distance( ST_transform(geom, 2163),
            ST_transform( ST_POINT(%s, %s, 4326), 2163))
        < (230.0 / 0.6214 * 1000.0)
    """,
        (
            NEXRAD_LON,
            NEXRAD_LAT,
            NEXRAD_LON,
            NEXRAD_LAT,
            sts,
            ets,
            NEXRAD_LON,
            NEXRAD_LAT,
        ),
    )
    print(f"Found {pcursor.rowcount} Lsrs between {sts} and {ets}")

    for row in pcursor:
        locx = radx + row["offset_x"]
        locy = rady + row["offset_y"]
        lon, lat = T_2163_4326.transform(locx, locy)
        # Locate nearest city and distance, hmm
        ncursor.execute(
            """
            SELECT name, ST_distance(ST_transform(geom, 2163),
            ST_POINT(%s, %s, 2163)) as d,
            %s - ST_x(ST_transform(geom,2163)) as offsetx,
            %s - ST_y(ST_transform(geom,2163)) as offsety
            from cities
            ORDER by d ASC LIMIT 1
        """,
            (
                locx,
                locy,
                locx,
                locy,
            ),
        )
        row2 = ncursor.fetchone()
        deg = getdir(0 - row2["offsetx"], 0 - row2["offsety"])
        drct = util.drct2text(deg)
        miles = row2["d"] * 0.0006214  # meters -> miles
        newcity = f"{miles:.1f} {drct} {row2['name']}"
        city = row["city"] if REAL88D == FAKE88D else newcity

        # Compute the new valid time
        ts = row["valid"]
        offset = (
            (ts - ARCHIVE_T0).days * 86400.0 + (ts - ARCHIVE_T0).seconds
        ) / SPEEDUP  # Speed up!
        valid = RT_T0 + timedelta(seconds=offset)
        print(f"{ts} -> {valid}")

        # Query for WFO
        ncursor.execute(
            """
        SELECT * from nws_ugc WHERE
   ST_transform(ST_POINT(%s, %s, 2163),4326) && geom
   and ST_Contains(geom,
           ST_transform(ST_POINT(%s, %s, 2163),4326))
        """,
            (
                locx,
                locy,
                locx,
                locy,
            ),
        )
        row2 = ncursor.fetchone()
        wfo = row["wfo"] if FAKE88D == REAL88D else row2["wfo"]
        cnty = row["county"] if FAKE88D == REAL88D else row2["name"]
        st = row["state"] if FAKE88D == REAL88D else row2["state"]

        # newremark = "%s\n[WAS: %s %s]" % (row['source'], row['city'],
        #                                  row['county'])
        # remark = row['remark'] if FAKE88D == REAL88D else newremark

        sql = """
        INSERT into lsrs(valid, type, magnitude, city, county, state,
        source, remark, wfo, typetext, geom, display_valid)
        values ('%s', '%s', %s, '%s',
        '%s', '%s', '%s', '%s', '%s', '%s',
        ST_POINT(%s, %s, 4326), '%s')
        """ % (
            valid.strftime("%Y-%m-%d %H:%M+00"),
            row["type"],
            row["magnitude"] or 0,
            city.replace("'", ""),
            cnty.replace("'", ""),
            st,
            row["source"],
            "" if row["remark"] is None else row["remark"].replace("'", ""),
            wfo,
            row["typetext"],
            lon,
            lat,
            valid.strftime("%Y-%m-%d %H:%M+00"),
        )
        ncursor.execute(sql)
        if wfo != "DMX":
            continue
        csvfp.write(
            ("%s,%s,%s,%.3f,%.3f,%s,%s,%s,%s,%s,%s\n")
            % (
                ts.strftime("%Y-%m-%d %H:%M"),
                f"{(ts.astimezone(timezone.utc)):%Y-%m-%d %H:%M}",
                valid.strftime("%Y-%m-%d %H:%M"),
                lon,
                lat,
                row["magnitude"],
                row["typetext"],
                row["source"],
                city,
                row["city"],
                ("" if row["remark"] is None else row["remark"]).replace(
                    ",", " "
                ),
            )
        )
    ncursor.close()
    NWA.commit()
    NWA.close()


def main():
    """Go main Go."""
    with open("/tmp/lsrs.csv", "w", encoding="utf-8") as fp:
        workflow(fp)
    print("Look at /tmp/lsrs.csv")


if __name__ == "__main__":
    main()
