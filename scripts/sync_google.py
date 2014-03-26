import psycopg2
mydb = psycopg2.connect('dbname=nwa')
mcursor = mydb.cursor()

mcursor.execute("""DELETE from lsrs where valid > '2014-01-31'""")
print 'Deleted %s rows' % (mcursor.rowcount,)

import sys
sys.path.insert(0, "/home/akrherz/projects/iem/scripts/cscap")
import util
import datetime
import pytz
from pyIEM import mesonet
import math
import ConfigParser
config = ConfigParser.ConfigParser()
config.read('/home/akrherz/projects/iem/scripts/cscap/mytokens.cfg')

# Shifting
time00 = datetime.datetime(2014,1,31,21,30)
time01 = datetime.datetime(2013,5,31,17,30)

time10 = datetime.datetime(2014,1,31,23,0)
time11 = datetime.datetime(2013,5,31,20,30)

newbase = datetime.datetime(2014,3,27,19,10)

speedup = (time11 - time01).seconds / float((time10 - time00).seconds)
print 'Speedup is %.4f' % (speedup,)

# Get me a client, stat
spr_client = util.get_spreadsheet_client(config)

feed = spr_client.get_list_feed("0AqZGw0coobCxdFpFSU9BYVVIRUhMNVV6c2xCcXh0b2c",
                                "od6")
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

lkp = {'HAIL': 'H',
       'TORNADO': 'T',
       'TSTM WND GST': 'G',
       'TSTM WND DMG': 'D',
       'NON-TSTM WND DMG': 'O',
       'NON-TSTM WND GST': 'N',
       'FUNNEL CLOUD': 'C',
       'HEAVY RAIN': 'R',
       'FLASH FLOOD': 'F',
       'WALL CLOUD': 'X',
       'LIGHTNING': 'L'}

for entry in feed.entry:
    data = entry.to_dict()
    #print data
    ts = datetime.datetime.strptime(data['workshoputc'], '%m/%d/%Y %H:%M:%S')
    displayts = ts
    if data['displaytimeutc'] is not None:
        displayts = datetime.datetime.strptime(data['displaytimeutc'], '%m/%d/%Y %H:%M:%S') + datetime.timedelta(seconds=120)
    #delta = (ts - time00).days * 86400. + (ts - time00).seconds
    #newts = newbase + datetime.timedelta(seconds=delta)
    #newts = ts - datetime.timedelta(minutes=30)
    #newtstamp = newts.strftime('%m/%d/%Y %H:%M:%S')
    #entry.set_value('workshoputc', newtstamp)
    
    if data['workshopcity'] is None:
        sql = """select name, ST_Distance(ST_Transform(
        ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'),26915), 
        ST_Transform(the_geom,26915)),
        ST_x(ST_Transform(ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'),26915)) - ST_x(ST_Transform(the_geom,26915)),
        ST_y(ST_Transform(ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'),26915)) - ST_y(ST_Transform(the_geom,26915))
        from cities_iowa 
        ORDER by st_distance ASC LIMIT 1""" % (data['lon'], data['lat'],
                                               data['lon'], data['lat'],
                                               data['lon'], data['lat']) 
        mcursor.execute(sql)
        row2 = mcursor.fetchone()
        print row2
        deg = getdir( 0 - row2[2], 0 - row2[3] )
        drct = mesonet.drct2dirTxt( deg )
        miles = row2[1] * 0.0006214  # meters -> miles
        entry.set_value('workshopcity',"%.1f %s %s" % (miles, drct, row2[0]))
        spr_client.update(entry) 
        print 'Updated'
    #print ts, newts, delta
    geo = 'SRID=4326;POINT(%s %s)' % (data['lon'], data['lat'])
    sql = """INSERT into lsrs (valid, display_valid, type, magnitude, city, source,
    remark, typetext, geom, wfo) values (%s, %s, %s, %s, %s, %s,
    %s, %s, %s, 'DMX')""" 
    args = (ts.strftime("%Y-%m-%d %H:%M+00"), displayts.strftime("%Y-%m-%d %H:%M+00"),
                lkp[ data['type']], data['magnitude'],
                data['workshopcity'], data['source'], data['remark'],
                data['type'], geo)
    mcursor.execute(sql, args)

mcursor.close()
mydb.commit()
