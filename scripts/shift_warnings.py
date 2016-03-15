"""
 Shift warnings around
"""
import psycopg2.extras
import pytz
import datetime
from pyiem.network import Table as NetworkTable
nt = NetworkTable("NEXRAD")
POSTGIS = psycopg2.connect(database="postgis",
                           host="mesonet.agron.iastate.edu", user='nobody')
pcursor = POSTGIS.cursor(cursor_factory=psycopg2.extras.DictCursor)
NWA = psycopg2.connect(database="nwa")
ncursor = NWA.cursor(cursor_factory=psycopg2.extras.DictCursor)

ncursor.execute("""DELETE from nwa_warnings where team = 'THE_WEATHER_BUREAU' and
  issue > 'TODAY'""")
print 'Removed %s rows from the nwa_warnings table' % (ncursor.rowcount,)

# First mesh point
ARCHIVE_T0 = datetime.datetime(2011, 5, 24, 20, 0)
ARCHIVE_T0 = ARCHIVE_T0.replace(tzinfo=pytz.timezone("UTC"))
RT_T0 = datetime.datetime(2015, 4, 2, 19, 30)  # 1:40 PM
RT_T0 = RT_T0.replace(tzinfo=pytz.timezone("UTC"))
# Second mesh point
ARCHIVE_T1 = datetime.datetime(2011, 5, 24, 23, 0)
ARCHIVE_T1 = ARCHIVE_T1.replace(tzinfo=pytz.timezone("UTC"))
RT_T1 = RT_T0 + datetime.timedelta(minutes=90)

SPEEDUP = (ARCHIVE_T1 - ARCHIVE_T0).seconds / float((RT_T1 - RT_T0).seconds)
print 'Speedup is %.2f' % (SPEEDUP,)


NEXRAD_LAT = nt.sts['TLX']['lat']
NEXRAD_LON = nt.sts['TLX']['lon']

# Get DMX coords in 26915
pcursor.execute("""SELECT 
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
print 'offsetx', offsetx
print 'offsety', offsety

# Get all the warnings
pcursor.execute("""SELECT *,
     ST_astext(ST_Transform(ST_Translate(ST_Transform(geom,26915),%s,%s),4236)) as tgeom
     from sbw_%s w 
     WHERE expire  > '%s' and issue < '%s' and significance = 'W'
     and phenomena in ('SV','TO') and status = 'NEW'
     and wfo in ('ICT', 'OUN', 'GLD', 'TOP', 'DDC', 'GID', 'EAX', 'TSA',
     'FWD', 'SGF', 'LZK', 'SHV') ORDER by issue ASC""" % (offsetx, 
   offsety, ARCHIVE_T1.year, 
   ARCHIVE_T0.strftime("%Y-%m-%d %H:%M+00"), ARCHIVE_T1.strftime("%Y-%m-%d %H:%M+00") 
    ) )

for row in pcursor:
    issue = row['issue']
    expire = row['expire']
    offset = ((issue - ARCHIVE_T0).days * 86400. +
              (issue - ARCHIVE_T0).seconds) / SPEEDUP  # Speed up!
    issue = RT_T0 + datetime.timedelta(seconds=offset)
    offset = ((expire - ARCHIVE_T0).days * 86400. +
              (expire - ARCHIVE_T0).seconds) / SPEEDUP  # Speed up!
    expire = RT_T0 + datetime.timedelta(seconds=offset)

    sql = """INSERT into nwa_warnings (issue, expire, gtype, wfo, eventid,
  status, phenomena, significance, geom, emergency, team) VALUES ('%s',
  '%s', 'P', 'DMX', %s, 'NEW', '%s', '%s', 'SRID=4326;%s', 'f', 
  'THE_WEATHER_BUREAU')""" % (issue.strftime("%Y-%m-%d %H:%M+00"), 
  expire.strftime("%Y-%m-%d %H:%M+00"), row['eventid'], row['phenomena'],
  row['significance'], row['tgeom'])
    print '--->', row['wfo'], row['issue'], sql
    ncursor.execute( sql )

ncursor.close()
NWA.commit()
NWA.close()
