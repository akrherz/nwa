# Need to shift LSRs in space and time, hmmm

import pg, math
import mx.DateTime
from pyIEM import mesonet
postgis = pg.connect("postgis", "iemdb", user='nobody')
nwa = pg.connect("nwa")

# Our window of LSRs in the database to move!
asts = mx.DateTime.DateTime(2008,6,5, 15) # 3 PM, 20 UTC
sts = mx.DateTime.DateTime(2008,6,5, 18) # 6 PM, 21 UTC <-- Start time
ests = mx.DateTime.DateTime(2008,6,5, 21) # 9 PM, 2 UTC

# What is the base time of our Shift # 2:10 so, 12:40
reftime = mx.DateTime.DateTime(2011,3,31,12,40)  # 90 min before 4 PM

def dir(u,v):
  if (v == 0):
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

# Get DMX coords in 26915
rs = postgis.query("""SELECT 
    x( transform( GeomFromEWKT('SRID=4326;POINT(-93.723892 41.731220)'), 26915)) as x,
    y( transform( GeomFromEWKT('SRID=4326;POINT(-93.723892 41.731220)'), 26915)) as y
    """).dictresult()
radx = rs[0]['x']
rady = rs[0]['y']

# Get all LSRs within 230m of the nexrad
rs = postgis.query("""SELECT *, astext(geom) as tgeom,
  x( transform( geom, 26915) ) - x( transform( GeomFromEWKT('SRID=4326;POINT(-96.232 38.997)'), 26915)) as offset_x,
  y( transform( geom, 26915) ) - y( transform( GeomFromEWKT('SRID=4326;POINT(-96.232 38.997)'), 26915)) as offset_y
     from lsrs_%s
     WHERE valid BETWEEN '%s' and '%s'
     and distance( transform(geom, 26915), 
         transform( GeomFromEWKT('SRID=4326;POINT(-96.232 38.997)'), 26915)) 
     < (230.0 / 0.6214 * 1000.0)""" % (asts.year, 
   asts.strftime("%Y-%m-%d %H:%M"), ests.strftime("%Y-%m-%d %H:%M") 
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
  deg = dir( 0 - rs2[0]['offsetx'], 0 - rs2[0]['offsety'] )
  drct = mesonet.drct2dirTxt( deg )
  miles = rs2[0]['d'] * 0.0006214  # meters -> miles
  city = "%.1f %s %s" % (miles, drct, rs2[0]['name'])

  # Compute the new valid time
  ts = mx.DateTime.strptime(rs[i]['valid'][:16], '%Y-%m-%d %H:%M')
  offset = (ts - asts).minutes / 2.0 # Speed up!
  valid = reftime + mx.DateTime.RelativeDateTime(minutes=offset)

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
        valid.strftime("%Y-%m-%d %H:%M"), rs[i]['type'], rs[i]['magnitude'],
        city, cnty, st, rs[i]['source'], rs[i]['remark'], wfo, 
        rs[i]['typetext'], locx, locy)
  print "%s %.0f %s %s" % (valid, miles, drct, city)
  nwa.query( sql )
