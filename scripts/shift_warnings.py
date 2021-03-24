"""
 Shift warnings around
"""
from __future__ import print_function
import datetime

import psycopg2.extras
from pandas.io.sql import read_sql
from pyiem.util import get_dbconn, utc
from pyiem.network import Table as NetworkTable


def main():
    """Go Main Go."""
    nt = NetworkTable("NEXRAD")
    POSTGIS = get_dbconn("postgis")
    pcursor = POSTGIS.cursor(cursor_factory=psycopg2.extras.DictCursor)
    NWA = psycopg2.connect(database="nwa")
    ncursor = NWA.cursor(cursor_factory=psycopg2.extras.DictCursor)

    ncursor.execute(
        """
        DELETE from nwa_warnings where team = 'THE_WEATHER_BUREAU' and
        issue > 'TODAY' and issue < 'TOMORROW'
    """
    )
    print("Removed %s rows from the nwa_warnings table" % (ncursor.rowcount,))

    orig0 = utc(2021, 3, 24, 18, 0)
    orig1 = orig0 + datetime.timedelta(minutes=600)

    workshop0 = utc(2021, 3, 24, 18, 0)
    workshop1 = workshop0 + datetime.timedelta(minutes=600)

    speedup = (orig1 - orig0).total_seconds() / (
        workshop1 - workshop0
    ).total_seconds()
    print("Overall Speedup is %.4f" % (speedup,))

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
    NEXRAD_LAT = nt.sts["FWS"]["lat"]
    NEXRAD_LON = nt.sts["FWS"]["lon"]
    tlx_coords = "SRID=4326;POINT(%s %s)" % (NEXRAD_LON, NEXRAD_LAT)
    pcursor.execute(
        """SELECT
        ST_x( ST_transform( ST_GeomFromEWKT('%s'), 2163)) as x,
        ST_y( ST_transform( ST_GeomFromEWKT('%s'), 2163)) as y
        """
        % (tlx_coords, tlx_coords)
    )
    row = pcursor.fetchone()
    radx = row["x"]
    rady = row["y"]

    offsetx = dmxx - radx
    offsety = dmxy - rady
    print("offsetx: %s" % (offsetx,))
    print("offsety: %s" % (offsety,))

    # Get all the warnings in the vicinity
    pcursor.execute(
        """
        SELECT *, ST_astext(ST_Transform(ST_Translate(ST_Transform(geom,
            2163),%s,%s),4236)) as tgeom
        from sbw_%s w
        WHERE expire  > '%s' and issue < '%s' and significance = 'W'
        and phenomena in ('SV','TO') and status = 'NEW'
        and wfo in ('FWD', 'OUN', 'TSA', 'SHV', 'HGX', 'EWX', 'SJT', 'EWX')
        ORDER by issue ASC
    """
        % (
            offsetx,
            offsety,
            orig0.year,
            orig0.strftime("%Y-%m-%d %H:%M+00"),
            orig1.strftime("%Y-%m-%d %H:%M+00"),
        )
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
        status, phenomena, significance, geom, emergency, team) VALUES ('%s',
        '%s', 'P', 'DMX', %s, 'NEW', '%s', '%s', 'SRID=4326;%s', 'f',
        'THE_WEATHER_BUREAU')
        """ % (
            issue.strftime("%Y-%m-%d %H:%M+00"),
            expire.strftime("%Y-%m-%d %H:%M+00"),
            eventid + 1,
            row["phenomena"],
            row["significance"],
            row["tgeom"],
        )
        # print('---> %s %s %s' % (row['wfo'], row['issue'], sql))
        ncursor.execute(sql)

    # Now cull any warnings that are outside of DMX
    df = read_sql(
        """
        SELECT u.wfo as ugc_wfo, w.ctid, w.wfo, w.phenomena, w.eventid from
        nwa_warnings w, nws_ugc u
        WHERE w.issue > 'TODAY' and w.issue < 'TOMORROW'
        and ST_Intersects(u.geom, w.geom)
        and w.team = 'THE_WEATHER_BUREAU'
        ORDER by w.wfo, w.eventid ASC
    """,
        NWA,
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
            "culling %s %s %s as outside of DMX"
            % (row["ugc_wfo"], row["phenomena"], row["eventid"])
        )
        ncursor2.execute(
            "DELETE from nwa_warnings where ctid = %s",
            (row["ctid"],),
        )

    ncursor.close()
    NWA.commit()
    NWA.close()


if __name__ == "__main__":
    main()
