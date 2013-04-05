"""
 Shift warnings around
"""

import pg, math
import mx.DateTime
postgis = pg.connect("postgis", "iemdb", user='nobody')
nwa = pg.connect("nwa")
nwa.query("SET TIME ZONE 'UTC'")
postgis.query("SET TIME ZONE 'UTC'")

nwa.query("""DELETE from nwa_warnings where team = 'THE_WEATHER_BUREAU' and
  issue > 'TODAY'""")

# First mesh point
ARCHIVE_T0 = mx.DateTime.DateTime(2012,2,29,4,4)
RT_T0 = mx.DateTime.DateTime(2013,4,4, 19, 10) # 2:10 PM
# Second mesh point
ARCHIVE_T1 = mx.DateTime.DateTime(2012,2,29,7,37)
RT_T1 = RT_T0 + mx.DateTime.RelativeDateTime(minutes=90) 

SPEEDUP = (ARCHIVE_T1 - ARCHIVE_T0).minutes / (RT_T1 - RT_T0).minutes
print 'Speedup is %.2f' % (SPEEDUP,)

# SGF
NEXRAD_LAT = 37.2352
NEXRAD_LON = -93.4004

# Get DMX coords in 26915
rs = postgis.query("""SELECT 
    x( transform( GeomFromEWKT('SRID=4326;POINT(-93.723892 41.731220)'), 26915)) as x,
    y( transform( GeomFromEWKT('SRID=4326;POINT(-93.723892 41.731220)'), 26915)) as y
    """).dictresult()
dmxx = rs[0]['x']
dmxy = rs[0]['y']

# TLX
tlx_coords = "SRID=4326;POINT(%s %s)" % (NEXRAD_LON, NEXRAD_LAT)
rs = postgis.query("""SELECT 
    x( transform( GeomFromEWKT('%s'), 26915)) as x,
    y( transform( GeomFromEWKT('%s'), 26915)) as y
    """ % (tlx_coords, tlx_coords)).dictresult()
radx = rs[0]['x']
rady = rs[0]['y']

offsetx = dmxx - radx
offsety = dmxy - rady
print 'offsetx', offsetx
print 'offsety', offsety

# Get all the warnings
rs = postgis.query("""SELECT *, 
     astext(ST_Transform(ST_Translate(ST_Transform(geom,26915),%s,%s),4236)) as tgeom
     from warnings_%s
     WHERE expire  > '%s' and issue < '%s' and significance = 'W'
     and phenomena in ('SV','TO') and gtype ='P' 
     and wfo = 'SGF' ORDER by issue ASC""" % (offsetx, 
   offsety, ARCHIVE_T1.year, 
   ARCHIVE_T0.strftime("%Y-%m-%d %H:%M"), ARCHIVE_T1.strftime("%Y-%m-%d %H:%M") 
    ) ).dictresult()

for i in range(len(rs)):
    issue = mx.DateTime.strptime(rs[i]['issue'][:16], '%Y-%m-%d %H:%M')
    expire = mx.DateTime.strptime(rs[i]['expire'][:16], '%Y-%m-%d %H:%M')
    offset = (issue - ARCHIVE_T0).minutes / SPEEDUP # Speed up!
    issue = RT_T0 + mx.DateTime.RelativeDateTime(minutes=offset)
    offset = (expire - ARCHIVE_T0).minutes / SPEEDUP # Speed up!
    expire = RT_T0 + mx.DateTime.RelativeDateTime(minutes=offset)

    sql = """INSERT into nwa_warnings (issue, expire, gtype, wfo, eventid,
  status, phenomena, significance, geom, emergency, team) VALUES ('%s',
  '%s', 'P', 'DMX', %s, 'NEW', '%s', '%s', 'SRID=4326;%s', 'f', 'THE_WEATHER_BUREAU')""" % (
issue.strftime("%Y-%m-%d %H:%M"), 
  expire.strftime("%Y-%m-%d %H:%M"), rs[i]['eventid'], rs[i]['phenomena'],
  rs[i]['significance'], rs[i]['tgeom']
  )
    print '--->', rs[i]['wfo'], rs[i]['issue'], sql
    nwa.query( sql )
