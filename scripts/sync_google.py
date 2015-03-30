import psycopg2
mydb = psycopg2.connect('dbname=nwa')
mcursor = mydb.cursor()

mcursor.execute("""DELETE from lsrs where valid > '2015-03-26'""")
print 'Deleted %s rows' % (mcursor.rowcount,)

import sys
sys.path.insert(0, "/home/akrherz/projects/iem/scripts/cscap")
# util is from cscap folder
import util
import datetime
import pytz
import math
import pyiem.util as pyiemutil
import ConfigParser
config = ConfigParser.ConfigParser()
config.read('/home/akrherz/projects/iem/scripts/cscap/mytokens.cfg')

# Shifting
time00 = datetime.datetime(2015, 3, 26, 18, 40)
time00 = time00.replace(tzinfo=pytz.timezone("UTC"))
#time01 = datetime.datetime(2015, 3, 26, 20, 10)

#time10 = datetime.datetime(2015, 2, 26, 23, 0)
#time11 = datetime.datetime(2015, 2, 27, 0, 30)

newbase = datetime.datetime(2015, 2, 26, 23, 0)
newbase = newbase.replace(tzinfo=pytz.timezone("UTC"))

# speedup = (time11 - time01).seconds / float((time10 - time00).seconds)
# print 'Speedup is %.4f' % (speedup,)

# Get me a client, stat
spr_client = util.get_spreadsheet_client(config)

feed = spr_client.get_list_feed("16MLYBh7-SiKR7ghANtTkMOhQN8s6-3z6TRVCDDRpuzM",
                                "od6")


def getdir(u, v):
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
       'FLOOD': 'F',
       'WALL CLOUD': 'X',
       'LIGHTNING': 'L'}

cdtbase = datetime.datetime.now()
cdtbase = cdtbase.replace(tzinfo=pytz.timezone("America/Chicago"), second=0,
                          microsecond=0)

for entry in feed.entry:
    data = entry.to_dict()
    # print data
    ts = datetime.datetime.strptime(data['workshoputc'], '%m/%d/%Y %H:%M:%S')
    ts = ts.replace(year=ts.year, month=ts.month, day=ts.day,
                    hour=ts.hour, minute=ts.minute,
                    tzinfo=pytz.timezone("UTC"))
    #if data['displaytimeutc'] is not None:
    #    displayts = datetime.datetime.strptime(data['displaytimeutc'], '%m/%d/%Y %H:%M:%S') + datetime.timedelta(seconds=120)
    delta = (ts - time00).days * 86400. + (ts - time00).seconds
    # newts = newbase + datetime.timedelta(seconds=delta)
    # print newbase, delta, newts, ts
    # newts = ts - datetime.timedelta(minutes=30)
    # newtstamp = newts.strftime('%m/%d/%Y %H:%M:%S')
    #entry.set_value('testrunutc', newtstamp)
    #spr_client.update(entry)

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
    # print row2
    #deg = getdir(0 - row2[2], 0 - row2[3])
    #drct = pyiemutil.drct2text(deg)
    #miles = row2[1] * 0.0006214  # meters -> miles
    #newcity = "%.1f %s %s" % (miles, drct, row2[0])
    #if data['workshopcity'] != newcity:
    #    print '%s -> %s' % (data['workshopcity'], newcity)
    #    entry.set_value('workshopcity', newcity)
    #    spr_client.update(entry)
    #    print 'Updated'
    #print ts, newts, delta
    geo = 'SRID=4326;POINT(%s %s)' % (data['lon'], data['lat'])
    sql = """INSERT into lsrs (valid, display_valid, type, magnitude, city, source,
    remark, typetext, geom, wfo) values (%s, %s, %s, %s, %s, %s,
    %s, %s, %s, 'DMX')"""
    args = (ts, ts,
                lkp[ data['type']], data['magnitude'],
                data['workshopcity'], data['source'], data['remark'],
                data['type'], geo)
    #print ts, newts
    mcursor.execute(sql, args)

mcursor.close()
mydb.commit()
