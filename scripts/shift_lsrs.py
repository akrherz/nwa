"""
 Need to shift LSRs in space and time
"""
import psycopg2.extras
import math
import datetime
import pytz
import pyiem.util as util
from pyiem.network import Table as NetworkTable
nt = NetworkTable("NEXRAD")
POSTGIS = psycopg2.connect(database="postgis",
                           host="mesonet.agron.iastate.edu", user='nobody')
pcursor = POSTGIS.cursor(cursor_factory=psycopg2.extras.DictCursor)
NWA = psycopg2.connect(database="nwa")
ncursor = NWA.cursor(cursor_factory=psycopg2.extras.DictCursor)

# First mesh point
ARCHIVE_T0 = datetime.datetime(2012,4,15,0,0)
ARCHIVE_T0 = ARCHIVE_T0.replace(tzinfo=pytz.timezone("UTC"))
RT_T0 = datetime.datetime(2015, 3, 26, 18, 40) # 1:40 PM
RT_T0 = RT_T0.replace(tzinfo=pytz.timezone("UTC"))
# Second mesh point
ARCHIVE_T1 = datetime.datetime(2012,4,15,3,45)
ARCHIVE_T1 = ARCHIVE_T1.replace(tzinfo=pytz.timezone("UTC"))
RT_T1 = RT_T0 + datetime.timedelta(minutes=90) 

SPEEDUP = (ARCHIVE_T1 - ARCHIVE_T0).seconds / float((RT_T1 - RT_T0).seconds)
print 'Speedup is %.2f' % (SPEEDUP,)

# Site NEXRAD
NEXRAD_LAT = nt.sts['ICT']['lat']
NEXRAD_LON = nt.sts['ICT']['lon']

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
    ''' Go!'''
    
    ncursor.execute("""
    DELETE from lsrs WHERE valid > %s and valid < %s
    """, (RT_T0 - datetime.timedelta(minutes=300),
          RT_T1 + datetime.timedelta(minutes=300)))
    print 'Removed %s rows from nwa lsr table' % (ncursor.rowcount,)
    
    # Get DMX coords in 26915
    pcursor.execute("""SELECT 
        ST_x( ST_transform( 
        ST_GeomFromEWKT('SRID=4326;POINT(-93.723892 41.731220)'), 26915)) as x,
        ST_y( ST_transform( 
        ST_GeomFromEWKT('SRID=4326;POINT(-93.723892 41.731220)'), 26915)) as y
        """)
    row = pcursor.fetchone()
    radx = row['x']
    rady = row['y']

    # Get all LSRs within 230m of the nexrad
    pcursor.execute("""SELECT *, ST_astext(geom) as tgeom,
        ST_x( ST_transform( geom, 26915) ) - 
            ST_x( ST_transform( 
                ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'), 26915)) as offset_x,
        ST_y( ST_transform( geom, 26915) ) - 
            ST_y( ST_transform( 
                ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'), 26915)) as offset_y
        from lsrs WHERE valid BETWEEN '%s' and '%s'
        and ST_distance( ST_transform(geom, 26915), 
            ST_transform( ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'), 26915)) 
        < (230.0 / 0.6214 * 1000.0)""" % (NEXRAD_LON, NEXRAD_LAT, 
                                          NEXRAD_LON, NEXRAD_LAT, 
(ARCHIVE_T0 - datetime.timedelta(minutes=120)).strftime("%Y-%m-%d %H:%M+00"), 
(ARCHIVE_T1 + datetime.timedelta(minutes=120)).strftime("%Y-%m-%d %H:%M+00"),
 NEXRAD_LON, NEXRAD_LAT
        ) )

    for row in pcursor:
        locx = radx + row['offset_x']
        locy = rady + row['offset_y']
        # Locate nearest city and distance, hmm
        sql = """SELECT name, ST_distance(ST_transform(the_geom,26915), 
   ST_GeomFromEWKT('SRID=26915;POINT(%s %s)')) as d,
   %s - ST_x(ST_transform(the_geom,26915)) as offsetx,
   %s - ST_y(ST_transform(the_geom,26915)) as offsety
   from cities_iowa 
   ORDER by d ASC LIMIT 1""" % (locx, locy, locx, locy) 
        ncursor.execute(sql)
        row2 = ncursor.fetchone()
        deg = getdir( 0 - row2['offsetx'], 0 - row2['offsety'] )
        drct = util.drct2text(deg)
        miles = row2['d'] * 0.0006214  # meters -> miles
        city = "%.1f %s %s" % (miles, drct, row2['name'])

        # Compute the new valid time
        ts = row['valid']
        offset = ((ts - ARCHIVE_T0).days * 86400. + 
                  (ts - ARCHIVE_T0).seconds) / SPEEDUP # Speed up!
        valid = RT_T0 + datetime.timedelta(seconds=offset)

        # Query for WFO
        sql = """SELECT * from nws_ugc WHERE 
   ST_transform(ST_GeomFromEWKT('SRID=26915;POINT(%s %s)'),4326) && geom
   and ST_Contains(geom, 
           ST_transform(ST_GeomFromEWKT('SRID=26915;POINT(%s %s)'),4326)) 
   """ % (locx, locy, locx, locy) 
        ncursor.execute(sql)
        row2 = ncursor.fetchone()
        wfo = row2['wfo']
        cnty = row2['name']
        st = row2['state']

        remark = "%s\n[WAS: %s %s]" % (row['source'], row['city'], 
            row['county'])

        sql = """INSERT into lsrs(valid, type, magnitude, city, county, state,
        source, remark, wfo, typetext, geom) values ('%s', '%s', %s, '%s',
        '%s', '%s', '%s', '%s', '%s', '%s', 
        ST_transform( ST_GeomFromEWKT('SRID=26915;POINT(%s %s)'),4326) )
        RETURNING ST_x(geom) as x, ST_y(geom) as y""" % (
            valid.strftime("%Y-%m-%d %H:%M+00"), row['type'], row['magnitude'],
            city.replace("'", ""), cnty.replace("'", ""), st, row['source'], 
            row['remark'], wfo, 
            row['typetext'], locx, locy)
        ncursor.execute( sql )
        row2 = ncursor.fetchone()
        print "%s,%s,%.3f,%.3f,%s,%s,%s,%s,%s,%s" % (ts.strftime("%Y-%m-%d %H:%M"),
                                        valid.strftime("%Y-%m-%d %H:%M"), 
                                        row2['x'], row2['y'],
                                        row['magnitude'], row['typetext'],
                                        row['source'],  city, row['city'],
                                        row['remark'])

main()
ncursor.close()
NWA.commit()
NWA.close()