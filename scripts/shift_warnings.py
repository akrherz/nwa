"""
Shift warnings around
"""

import json
from datetime import datetime, timedelta, timezone

import click
import pandas as pd
from pyiem.database import get_dbconnc, get_sqlalchemy_conn, sql_helper
from pyiem.network import Table as NetworkTable


@click.command()
@click.option("--nexrad", default="DMX", help="NEXRAD Site to Fake")
def main(nexrad: str):
    """Go Main Go."""
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

    nt = NetworkTable("NEXRAD")
    POSTGIS, pcursor = get_dbconnc("postgis")
    NWA, ncursor = get_dbconnc("nwa", host="localhost")

    ncursor.execute(
        "DELETE from nwa_warnings where team = 'THE_WEATHER_BUREAU' and "
        "issue > '2025-03-27' and issue < '2025-03-28'"
    )
    print(f"Removed {ncursor.rowcount} rows from the nwa_warnings table")

    NEXRAD_LAT = nt.sts[nexrad]["lat"]
    NEXRAD_LON = nt.sts[nexrad]["lon"]

    # Get DMX coords in 2163
    pcursor.execute(
        """
        SELECT
        ST_x( ST_transform(ST_Point(%s, %s, 4326), 2163)) as x,
        ST_y( ST_transform(ST_Point(%s, %s, 4326), 2163)) as y
    """,
        (NEXRAD_LON, NEXRAD_LAT, NEXRAD_LON, NEXRAD_LAT),
    )
    row = pcursor.fetchone()
    dmxx = row["x"]
    dmxy = row["y"]

    # TLX or whatever RADAR we are offsetting too
    NEXRAD_LAT = nt.sts[cfg["nexrad"]]["lat"]
    NEXRAD_LON = nt.sts[cfg["nexrad"]]["lon"]
    pcursor.execute(
        """SELECT
        ST_x( ST_transform( ST_Point(%s, %s, 4326), 2163)) as x,
        ST_y( ST_transform( ST_Point(%s, %s, 4326), 2163)) as y
        """,
        (NEXRAD_LON, NEXRAD_LAT, NEXRAD_LON, NEXRAD_LAT),
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
        """
        SELECT *, ST_astext(ST_Transform(ST_Translate(ST_Transform(geom,
            2163),%s,%s),4236)) as tgeom
        from sbw w
        WHERE vtec_year = %s and expire  > %s and issue < %s
        and significance = 'W' and phenomena in ('SV','TO') and status = 'NEW'
        ORDER by issue ASC
    """,
        (
            offsetx,
            offsety,
            timing["archive_begin"].year,
            timing["archive_begin"] - timedelta(minutes=300),
            timing["archive_end"] + timedelta(minutes=300),
        ),
    )

    # need to rewrite the eventids
    for eventid, row in enumerate(pcursor):
        issue = row["issue"]
        expire = row["expire"]
        offset = (
            (issue - timing["archive_begin"]).days * 86400.0
            + (issue - timing["archive_begin"]).seconds
        ) / speedup  # Speed up!
        issue = timing["workshop_begin"] + timedelta(seconds=offset)
        offset = (
            (expire - timing["archive_begin"]).days * 86400.0
            + (expire - timing["archive_begin"]).seconds
        ) / speedup  # Speed up!
        expire = timing["workshop_begin"] + timedelta(seconds=offset)

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
        df = pd.read_sql(
            sql_helper("""
            SELECT u.wfo as ugc_wfo, w.ctid, w.wfo, w.phenomena, w.eventid
            from nwa_warnings w, nws_ugc u
            WHERE w.issue > :sts and w.issue < :ets
            and ST_Intersects(u.geom, w.geom)
            and w.team = 'THE_WEATHER_BUREAU'
            ORDER by w.wfo, w.eventid ASC
        """),
            conn,
            index_col=None,
            params={
                "sts": timing["workshop_begin"].replace(hour=0, minute=0),
                "ets": timing["workshop_end"].replace(hour=23, minute=59),
            },
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
        "UPDATE nwa_warnings SET issue = %s WHERE "
        "team = 'THE_WEATHER_BUREAU' and issue < %s and "
        "expire > %s",
        (
            timing["workshop_begin"],
            timing["workshop_begin"],
            timing["workshop_begin"],
        ),
    )
    print(f"Goosed {ncursor2.rowcount} issuance times... MANUAL 2HACK")

    ncursor2.close()
    NWA.commit()
    NWA.close()


if __name__ == "__main__":
    main()
