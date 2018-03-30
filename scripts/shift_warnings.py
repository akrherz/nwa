"""
 Shift warnings around
"""
from __future__ import print_function
import datetime

import psycopg2.extras
import pytz
from pyiem.util import get_dbconn
from pyiem.network import Table as NetworkTable
nt = NetworkTable("NEXRAD")
POSTGIS = get_dbconn("postgis")
pcursor = POSTGIS.cursor(cursor_factory=psycopg2.extras.DictCursor)
NWA = psycopg2.connect(database="nwa")
ncursor = NWA.cursor(cursor_factory=psycopg2.extras.DictCursor)

ncursor.execute("""
    DELETE from nwa_warnings where team = 'THE_WEATHER_BUREAU' and
    issue > 'TODAY'
    """)
print('Removed %s rows from the nwa_warnings table' % (ncursor.rowcount,))

orig0 = datetime.datetime(2017, 6, 28, 20, 30)
orig0 = orig0.replace(tzinfo=pytz.utc)
orig1 = orig0 + datetime.timedelta(minutes=180)

workshop0 = datetime.datetime(2018, 3, 22, 19, 0)
workshop0 = workshop0.replace(tzinfo=pytz.utc)
workshop1 = workshop0 + datetime.timedelta(minutes=90)

speedup = ((orig1 - orig0).total_seconds() /
           (workshop1 - workshop0).total_seconds())
print('Overall Speedup is %.4f' % (speedup,))


NEXRAD_LAT = nt.sts['DMX']['lat']
NEXRAD_LON = nt.sts['DMX']['lon']

# Get DMX coords in 26915
pcursor.execute("""
    SELECT
    ST_x( ST_transform(
        ST_GeomFromEWKT('SRID=4326;POINT(-93.723892 41.731220)'), 26915)) as x,
    ST_y( ST_transform(
        ST_GeomFromEWKT('SRID=4326;POINT(-93.723892 41.731220)'), 26915)) as y
    """)
row = pcursor.fetchone()
dmxx = row['x']
dmxy = row['y']

# TLX
tlx_coords = "SRID=4326;POINT(%s %s)" % (NEXRAD_LON, NEXRAD_LAT)
pcursor.execute("""SELECT
    ST_x( ST_transform( ST_GeomFromEWKT('%s'), 26915)) as x,
    ST_y( ST_transform( ST_GeomFromEWKT('%s'), 26915)) as y
    """ % (tlx_coords, tlx_coords))
row = pcursor.fetchone()
radx = row['x']
rady = row['y']

offsetx = dmxx - radx
offsety = dmxy - rady
print('offsetx: %s' % (offsetx, ))
print('offsety: %s' % (offsety, ))

# Get all the warnings
pcursor.execute("""SELECT *,
     ST_astext(ST_Transform(ST_Translate(ST_Transform(geom,
         26915),%s,%s),4236)) as tgeom
     from sbw_%s w
     WHERE expire  > '%s' and issue < '%s' and significance = 'W'
     and phenomena in ('SV','TO') and status = 'NEW'
     and wfo in ('DMX') ORDER by issue ASC
     """ % (offsetx, offsety, orig0.year,
            orig0.strftime("%Y-%m-%d %H:%M+00"),
            orig1.strftime("%Y-%m-%d %H:%M+00")))

for row in pcursor:
    issue = row['issue']
    expire = row['expire']
    offset = ((issue - orig0).days * 86400. +
              (issue - orig0).seconds) / speedup  # Speed up!
    issue = workshop0 + datetime.timedelta(seconds=offset)
    offset = ((expire - orig0).days * 86400. +
              (expire - orig0).seconds) / speedup  # Speed up!
    expire = workshop0 + datetime.timedelta(seconds=offset)

    sql = """
    INSERT into nwa_warnings (issue, expire, gtype, wfo, eventid,
    status, phenomena, significance, geom, emergency, team) VALUES ('%s',
    '%s', 'P', 'DMX', %s, 'NEW', '%s', '%s', 'SRID=4326;%s', 'f',
    'THE_WEATHER_BUREAU')
    """ % (issue.strftime("%Y-%m-%d %H:%M+00"),
           expire.strftime("%Y-%m-%d %H:%M+00"),
           row['eventid'], row['phenomena'],
           row['significance'], row['tgeom'])
    print('---> %s %s %s' % (row['wfo'], row['issue'], sql))
    ncursor.execute(sql)

ncursor.close()
NWA.commit()
NWA.close()
