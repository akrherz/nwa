"""
 Shift warnings around
"""
import datetime

import psycopg2.extras
from pandas.io.sql import read_sql
from pyiem.network import Table as NetworkTable
from pyiem.util import get_dbconn, get_sqlalchemy_conn, utc


def main():
    """Go Main Go."""
    nt = NetworkTable("NEXRAD")
    POSTGIS = get_dbconn("postgis")
    pcursor = POSTGIS.cursor(cursor_factory=psycopg2.extras.DictCursor)
    NWA = get_dbconn("nwa", host="localhost")
    ncursor = NWA.cursor(cursor_factory=psycopg2.extras.DictCursor)

    ncursor.execute(
        "DELETE from nwa_warnings where team = 'THE_WEATHER_BUREAU' and "
        "issue > 'TODAY' and issue < 'TOMORROW'"
    )
    print(f"Removed {ncursor.rowcount} rows from the nwa_warnings table")

    orig0 = utc(2013, 5, 20, 19, 12)
    orig1 = orig0 + datetime.timedelta(minutes=134)

    workshop0 = utc(2023, 3, 23, 19, 30)
    workshop1 = workshop0 + datetime.timedelta(minutes=90)

    speedup = (orig1 - orig0).total_seconds() / (
        workshop1 - workshop0
    ).total_seconds()
    print(f"Overall Speedup is {speedup:.4f}")

    NEXRAD_LAT = nt.sts["DMX"]["lat"]
    NEXRAD_LON = nt.sts["DMX"]["lon"]

    # Get DMX coords in 2163
    pcursor.execute(
        """
        SELECT
        ST_x( ST_transform(
            ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'), 2163)) as x,
        ST_y( ST_transform(
            ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'), 2163)) as y
    """,
        (NEXRAD_LON, NEXRAD_LAT, NEXRAD_LON, NEXRAD_LAT),
    )
    row = pcursor.fetchone()
    dmxx = row["x"]
    dmxy = row["y"]

    # TLX or whatever RADAR we are offsetting too
    NEXRAD_LAT = nt.sts["TLX"]["lat"]
    NEXRAD_LON = nt.sts["TLX"]["lon"]
    tlx_coords = f"SRID=4326;POINT({NEXRAD_LON} {NEXRAD_LAT})"
    pcursor.execute(
        """SELECT
        ST_x( ST_transform( ST_GeomFromEWKT(%s), 2163)) as x,
        ST_y( ST_transform( ST_GeomFromEWKT(%s), 2163)) as y
        """,
        (tlx_coords, tlx_coords),
    )
    row = pcursor.fetchone()
    radx = row["x"]
    rady = row["y"]

    offsetx = dmxx - radx
    offsety = dmxy - rady
    print(f"offsetx: {offsetx}")
    print(f"offsety: {offsety}")

    # Get all the warnings in the vicinity
    pcursor.execute(
        f"""
        SELECT *, ST_astext(ST_Transform(ST_Translate(ST_Transform(geom,
            2163),%s,%s),4236)) as tgeom
        from sbw_{orig0.year} w
        WHERE expire  > %s and issue < %s and significance = 'W'
        and phenomena in ('SV','TO') and status = 'NEW'
        ORDER by issue ASC
    """,
        (
            offsetx,
            offsety,
            orig0 - datetime.timedelta(minutes=300),
            orig1 + datetime.timedelta(minutes=300),
        ),
    )

    # need to rewrite the eventids
    for eventid, row in enumerate(pcursor):
        issue = row["issue"]
        expire = row["expire"]
        offset = (
            (issue - orig0).days * 86400.0 + (issue - orig0).seconds
        ) / speedup  # Speed up!
        issue = workshop0 + datetime.timedelta(seconds=offset)
        offset = (
            (expire - orig0).days * 86400.0 + (expire - orig0).seconds
        ) / speedup  # Speed up!
        expire = workshop0 + datetime.timedelta(seconds=offset)

        sql = """
        INSERT into nwa_warnings (issue, expire, gtype, wfo, eventid,
        status, phenomena, significance, geom, emergency, team) VALUES (%s,
        %s, 'P', 'DMX', %s, 'NEW', %s, %s, ST_GeomFromText(%s, 4326), 'f',
        'THE_WEATHER_BUREAU')
        """
        args = (
            issue,
            expire,
            eventid + 1,
            row["phenomena"],
            row["significance"],
            row["tgeom"],
        )
        # print('---> %s %s %s' % (row['wfo'], row['issue'], sql))
        ncursor.execute(sql, args)
    ncursor.close()
    NWA.commit()

    # Now cull any warnings that are outside of DMX
    with get_sqlalchemy_conn("nwa", host="localhost") as conn:
        df = read_sql(
            """
            SELECT u.wfo as ugc_wfo, w.ctid, w.wfo, w.phenomena, w.eventid
            from nwa_warnings w, nws_ugc u
            WHERE w.issue > 'TODAY' and w.issue < 'TOMORROW'
            and ST_Intersects(u.geom, w.geom)
            and w.team = 'THE_WEATHER_BUREAU'
            ORDER by w.wfo, w.eventid ASC
        """,
            conn,
            index_col=None,
        )
    print(f"Found {len(df.index)} warnings to consider culling...")
    hits = df[df["ugc_wfo"] == "DMX"]

    ncursor2 = NWA.cursor()
    for _, row in df.iterrows():
        if row["ugc_wfo"] == "DMX":
            continue
        if row["ctid"] in hits["ctid"].values:
            continue
        print(
            f"culling {row['ugc_wfo']} {row['phenomena']} {row['eventid']} "
            "as outside of DMX"
        )
        ncursor2.execute(
            "DELETE from nwa_warnings where ctid = %s",
            (row["ctid"],),
        )

    # Since NWS was not confined to a start time, we need to goose the
    # issuance time
    ncursor2.execute(
        "UPDATE nwa_warnings SET issue = '2023-03-23 19:00+00' WHERE "
        "team = 'THE_WEATHER_BUREAU' and issue < '2023-03-23 19:00+00' and "
        "expire > '2023-03-23 19:00+00'"
    )
    print(f"Goosed {ncursor2.rowcount} issuance times... MANUAL 2023 HACK")

    ncursor2.close()
    NWA.commit()
    NWA.close()


if __name__ == "__main__":
    main()
