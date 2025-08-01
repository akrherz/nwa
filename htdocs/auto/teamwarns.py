"""Map a Team's warnings and perhaps more!"""

import json
import os
from datetime import datetime, timezone
from io import BytesIO

import geopandas as gpd
from matplotlib.image import imread
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from paste.request import parse_formvars
from pyiem.database import get_sqlalchemy_conn, sql_helper
from pyiem.plot import MapPlot

PATH = "/opt/nwa/htdocs/icons"
ZOOM = 0.6


def application(environ, start_response):
    """mod_wsgi handler."""
    configdir = os.path.join(os.path.dirname(__file__), "../..", "config")
    with open(f"{configdir}/workshop.json") as fh:
        cfg = json.load(fh)
    timing = cfg["timing"]
    for key in timing:
        timing[key] = datetime.strptime(
            timing[key], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)

    ICONS = {
        "D": OffsetImage(imread(f"{PATH}/winddamage.png"), zoom=ZOOM),
        "G": OffsetImage(imread(f"{PATH}/wind.png"), zoom=ZOOM),
        "H": OffsetImage(imread(f"{PATH}/hail.png"), zoom=ZOOM),
        "L": OffsetImage(imread(f"{PATH}/lightning.gif"), zoom=ZOOM),
        "N": OffsetImage(imread(f"{PATH}/wind.png"), zoom=ZOOM),
        "O": OffsetImage(imread(f"{PATH}/winddamage.png"), zoom=ZOOM),
        "T": OffsetImage(imread(f"{PATH}/tornado.png"), zoom=ZOOM - 0.2),
    }
    form = parse_formvars(environ)
    team = form.get("team", "THE_WEATHER_BUREAU")
    params = {
        "sts": timing["workshop_begin"],
        "ets": timing["workshop_end"],
        "team": team,
    }

    with get_sqlalchemy_conn("nwa") as conn:
        warndf = gpd.read_postgis(
            sql_helper(
                """
    SELECT geom, case when phenomena = 'TO' then 'r' else 'yellow' end as color
    from nwa_warnings where expire > :sts and issue < :ets
    and team = :team ORDER by issue ASC"""
            ),
            conn,
            geom_col="geom",
            params=params,
            crs="EPSG:4326",
        )  # type: ignore
        lsrdf = gpd.read_postgis(
            sql_helper(
                """
    SELECT geom, type
    from lsrs where valid >= :sts and valid < :ets and wfo = 'DMX'
    and (type in ('T', 'D') or (type = 'G' and magnitude > 57)
    or (type = 'H' and magnitude >= 1)) ORDER by valid ASC"""
            ),
            conn,
            geom_col="geom",
            params=params,
            crs="EPSG:4326",
        )  # type: ignore

    mp = MapPlot(
        figsize=(8, 8),
        sector="cwa",
        continentalcolor="tan",
        caption="2024 NWA Workshop",
        title=f"{team} Warnings for 2024 CWA Workshop",
        subtitle=(
            f"{len(warndf.index)} Warnings, {len(lsrdf.index)} LSRs "
            f"between {timing['workshop_begin']:%H%M}Z and "
            f"{timing['workshop_end']:%H%M}Z"
        ),
        cwa="DMX",
        # logo="nwa",
    )
    mp.draw_cwas()
    mp.drawcounties()

    warndf.to_crs(mp.panels[0].crs).plot(
        ax=mp.panels[0].ax,
        aspect=None,
        edgecolor=warndf["color"],
        facecolor="None",
        lw=3,
        zorder=22,
    )
    for _i, row in lsrdf.to_crs(mp.panels[0].crs).iterrows():
        mp.panels[0].ax.add_artist(
            AnnotationBbox(
                ICONS[row["type"]],
                *row["geom"].coords,
                frameon=False,
                zorder=21 if row["type"] == "T" else 20,
            )
        )

    bio = BytesIO()
    mp.fig.savefig(bio, format="png")
    mp.close()
    start_response("200 OK", [("Content-type", "image/png")])
    return [bio.getvalue()]
