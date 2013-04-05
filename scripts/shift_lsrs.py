"""
 Need to shift LSRs in space and time, hmmm
"""

import pg
import math
import mx.DateTime
from pyIEM import mesonet
postgis = pg.connect("postgis", "iemdb", user='nobody')
postgis.query("SET TIME ZONE 'GMT'")
nwa = pg.connect("nwa")

# First mesh point
ARCHIVE_T0 = mx.DateTime.DateTime(2012,2,29,4,23)
RT_T0 = mx.DateTime.DateTime(2013,2,12,19,50) # 2:30 PM
# Second mesh point
ARCHIVE_T1 = mx.DateTime.DateTime(2012,2,29,7,37)
RT_T1 = RT_T0 + mx.DateTime.RelativeDateTime(minutes=90) 

SPEEDUP = (ARCHIVE_T1 - ARCHIVE_T0).minutes / (RT_T1 - RT_T0).minutes
print 'Speedup is %.2f' % (SPEEDUP,)

# SGF
NEXRAD_LAT = 37.2352
NEXRAD_LON = -93.4004

def getdir(u,v):
    if v == 0:
        v = 0.000000001
    dd = math.atan(u / v)
    ddir = (dd * 180.00) / math.pi

    if (u > 0 and v > 0 ): # First Quad
        ddir = 180 + ddir
    elif (u > 0 and v < 0 ): # Second Quad
        ddir = 360 + ddir
    elif (u < 0 and v < 0 ): # Third Quad
        ddir = ddir
    elif (u < 0 and v > 0 ): # Fourth Quad
        ddir = 180 + ddir

    return int(math.fabs(ddir))

def main():
    # Get DMX coords in 26915
    rs = postgis.query("""SELECT 
        x( transform( GeomFromEWKT('SRID=4326;POINT(-93.723892 41.731220)'), 26915)) as x,
        y( transform( GeomFromEWKT('SRID=4326;POINT(-93.723892 41.731220)'), 26915)) as y
        """).dictresult()
    radx = rs[0]['x']
    rady = rs[0]['y']

    # Get all LSRs within 230m of the nexrad
    rs = postgis.query("""SELECT *, astext(geom) as tgeom,
        x( transform( geom, 26915) ) - x( transform( GeomFromEWKT('SRID=4326;POINT(%s %s)'), 26915)) as offset_x,
        y( transform( geom, 26915) ) - y( transform( GeomFromEWKT('SRID=4326;POINT(%s %s)'), 26915)) as offset_y
        from lsrs WHERE valid BETWEEN '%s' and '%s'
        and distance( transform(geom, 26915), 
        transform( GeomFromEWKT('SRID=4326;POINT(%s %s)'), 26915)) 
        < (230.0 / 0.6214 * 1000.0)""" % (NEXRAD_LON, NEXRAD_LAT, 
                                          NEXRAD_LON, NEXRAD_LAT, 
(ARCHIVE_T0 - mx.DateTime.RelativeDateTime(minutes=120)).strftime("%Y-%m-%d %H:%M+00"), 
(ARCHIVE_T1 + mx.DateTime.RelativeDateTime(minutes=120)).strftime("%Y-%m-%d %H:%M+00"),
 NEXRAD_LON, NEXRAD_LAT
        ) ).dictresult()

    for i in range(len(rs)):
        locx = radx + rs[i]['offset_x']
        locy = rady + rs[i]['offset_y']
        # Locate nearest city and distance, hmm
        sql = """SELECT name, distance(transform(the_geom,26915), 
   GeomFromEWKT('SRID=26915;POINT(%s %s)')) as d,
   %s - x(transform(the_geom,26915)) as offsetx,
   %s - y(transform(the_geom,26915)) as offsety
   from cities_iowa 
   ORDER by d ASC LIMIT 1""" % (locx, locy, locx, locy) 
        rs2 = nwa.query(sql).dictresult()
        deg = getdir( 0 - rs2[0]['offsetx'], 0 - rs2[0]['offsety'] )
        drct = mesonet.drct2dirTxt( deg )
        miles = rs2[0]['d'] * 0.0006214  # meters -> miles
        city = "%.1f %s %s" % (miles, drct, rs2[0]['name'])

        # Compute the new valid time
        ts = mx.DateTime.strptime(rs[i]['valid'][:16], '%Y-%m-%d %H:%M')
        offset = (ts - ARCHIVE_T0).minutes / SPEEDUP # Speed up!
        valid = RT_T0 + mx.DateTime.RelativeDateTime(minutes=offset)

        # Query for WFO
        sql = """SELECT * from nws_ugc WHERE 
   transform(GeomFromEWKT('SRID=26915;POINT(%s %s)'),4326) && geom
   and ST_Contains(geom, transform(GeomFromEWKT('SRID=26915;POINT(%s %s)'),4326)) 
   """ % (locx, locy, locx, locy) 
        rs2 = nwa.query(sql).dictresult()
        wfo = rs2[0]['wfo']
        cnty = rs2[0]['name']
        st = rs2[0]['state']

        remark = "%s\n[WAS: %s %s]" % (rs[i]['source'], rs[i]['city'], 
            rs[i]['county'])

        sql = """INSERT into lsrs(valid, type, magnitude, city, county, state,
        source, remark, wfo, typetext, geom) values ('%s', '%s', %s, '%s',
        '%s', '%s', '%s', '%s', '%s', '%s', 
        transform( GeomFromEWKT('SRID=26915;POINT(%s %s)'),4326) )""" % (
        valid.strftime("%Y-%m-%d %H:%M+00"), rs[i]['type'], rs[i]['magnitude'],
        city.replace("'", ""), cnty.replace("'", ""), st, rs[i]['source'], rs[i]['remark'], wfo, 
        rs[i]['typetext'], locx, locy)
        print "%s,%s,%s,%s,%s,%s" % (valid.strftime("%Y-%m-%d %H:%M"), 
                                        rs[i]['magnitude'], rs[i]['typetext'],
                                        rs[i]['source'],  city,
                                        rs[i]['remark'])
        nwa.query( sql )

main()