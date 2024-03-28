"""Convert old county warnings into simple polygons"""

import datetime

import psycopg2
import pytz

iempgconn = psycopg2.connect("postgis")
iemcursor = iempgconn.cursor()

pgconn = psycopg2.connect(database="nwa")
cursor = pgconn.cursor()

cursor.execute(
    """DELETE from nwa_warnings where issue > '2016-03-31'
 and team = 'THE_WEATHER_BUREAU'"""
)
print("removed %s entries" % (cursor.rowcount,))

# ______________________________________________________________________
# Upstream is sync_google!
orig0 = datetime.datetime(1999, 4, 8, 19, 37)
orig0 = orig0.replace(tzinfo=pytz.timezone("UTC"))
origB = orig0.replace(hour=20, minute=50)
orig1 = orig0.replace(hour=23, minute=16)

workshop0 = datetime.datetime(2016, 3, 31, 18, 10)
workshop0 = workshop0.replace(tzinfo=pytz.timezone("UTC"))
workshopB1 = workshop0.replace(hour=18, minute=40)
workshopB2 = workshop0.replace(hour=18, minute=50)
workshop1 = workshop0.replace(hour=19, minute=50)

speedup = (orig1 - orig0).total_seconds() / (
    workshop1 - workshop0
).total_seconds()
print("Overall Speedup is %.4f" % (speedup,))
speedup1 = (origB - orig0).total_seconds() / (
    workshopB1 - workshop0
).total_seconds()
print("Par1    Speedup is %.4f" % (speedup1,))
speedup2 = (orig1 - origB).total_seconds() / (
    workshop1 - workshopB2
).total_seconds()
print("Part2   Speedup is %.4f" % (speedup2,))


def warp(lsrtime):
    """Convert the LSR Time to our workshop time, of some sort"""
    base = orig0 if lsrtime < origB else origB
    newbase = workshop0 if lsrtime < origB else workshopB2
    _speedup = speedup1 if lsrtime < origB else speedup2
    return newbase + datetime.timedelta(
        seconds=((lsrtime - base).total_seconds() / _speedup)
    )


# ______________________________________________________________________

iemcursor.execute(
    """SELECT ST_astext(ST_Simplify(geom, 0.1)),
 issue at time zone 'UTC', expire at time zone 'UTC',
 phenomena, significance, eventid
 from warnings_1999 w JOIN ugcs u on (w.gid = u.gid) WHERE
 w.wfo = 'DMX' and issue > '1999-04-08' and issue < '1999-04-09' ORDER by issue
 """
)
for row in iemcursor:
    geo = row[0]
    issue = row[1].replace(tzinfo=pytz.timezone("UTC"))
    expire = row[2].replace(tzinfo=pytz.timezone("UTC"))
    phenomena = row[3]
    significance = row[4]
    eventid = row[5]

    cursor.execute(
        """INSERT into nwa_warnings(issue, expire, wfo, eventid,
     status, phenomena, significance, geom, emergency, team, gtype)
     VALUES (%s, %s, 'DMX', %s, 'NEW', %s, %s, %s, 'f', 'THE_WEATHER_BUREAU',
     'P')
     """,
        (
            warp(issue),
            warp(expire),
            eventid,
            phenomena,
            significance,
            "SRID=4326;%s" % (geo,),
        ),
    )

cursor.close()
pgconn.commit()
