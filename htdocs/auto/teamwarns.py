"""Map a Team's warnings and perhaps more!"""
from io import BytesIO

from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import geopandas as gpd
from paste.request import parse_formvars
from pyiem.util import get_sqlalchemy_conn, utc
from pyiem.plot.use_agg import plt
from pyiem.plot import MapPlot

STS = utc(2023, 4, 20, 19, 30)
ETS = utc(2023, 4, 20, 21, 0)
PATH = "/opt/nwa/htdocs/icons"
ZOOM = 0.6


def application(environ, start_response):
    """mod_wsgi handler."""
    ICONS = {
        "D": OffsetImage(plt.imread(f"{PATH}/winddamage.png"), zoom=ZOOM),
        "G": OffsetImage(plt.imread(f"{PATH}/wind.png"), zoom=ZOOM),
        "H": OffsetImage(plt.imread(f"{PATH}/hail.png"), zoom=ZOOM),
        "L": OffsetImage(plt.imread(f"{PATH}/lightning.gif"), zoom=ZOOM),
        "N": OffsetImage(plt.imread(f"{PATH}/wind.png"), zoom=ZOOM),
        "O": OffsetImage(plt.imread(f"{PATH}/winddamage.png"), zoom=ZOOM),
        "T": OffsetImage(plt.imread(f"{PATH}/tornado.png"), zoom=ZOOM - 0.2),
    }
    form = parse_formvars(environ)
    team = form.get("team", "THE_WEATHER_BUREAU")

    with get_sqlalchemy_conn("nwa") as conn:
        warndf = gpd.read_postgis(
            "SELECT geom, "
            "case when phenomena = 'TO' then 'r' else 'yellow' end as color "
            "from nwa_warnings where expire > %s and issue < %s and team = %s "
            "ORDER by issue ASC",
            conn,
            geom_col="geom",
            params=(STS, ETS, team),
            crs="EPSG:4326",
        )
        lsrdf = gpd.read_postgis(
            "SELECT geom, "
            "type "
            "from lsrs where valid >= %s and valid < %s and wfo = 'DMX' "
            "and (type in ('T', 'D') or (type = 'G' and magnitude > 57) "
            " or (type = 'H' and magnitude >= 1)) "
            "ORDER by valid ASC",
            conn,
            geom_col="geom",
            params=(STS, ETS),
            crs="EPSG:4326",
        )

    mp = MapPlot(
        figsize=(8, 8),
        sector="cwa",
        continentalcolor="tan",
        caption="2023 MT417 Workshop",
        title=f"{team} Warnings for 2023 MT417 Workshop",
        subtitle=(
            f"{len(warndf.index)} Warnings, {len(lsrdf.index)} LSRs "
            f"between {STS:%H%M}Z and {ETS:%H%M}Z"
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
