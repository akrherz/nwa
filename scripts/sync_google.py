import psycopg2
import sys
# util is from cscap folder
import pyiem.cscap_utils as util
import datetime
import pytz
import math
import pyiem.util as pyiemutil

mydb = psycopg2.connect('dbname=nwa')
mcursor = mydb.cursor()
mcursor.execute("""DELETE from lsrs where valid > '2016-03-31'""")
print 'Deleted %s rows' % (mcursor.rowcount,)

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

speedup = ((orig1 - orig0).total_seconds() /
           (workshop1 - workshop0).total_seconds())
print 'Overall Speedup is %.4f' % (speedup,)
speedup1 = ((origB - orig0).total_seconds() /
            (workshopB1 - workshop0).total_seconds())
print 'Par1    Speedup is %.4f' % (speedup1,)
speedup2 = ((orig1 - origB).total_seconds() /
            (workshop1 - workshopB2).total_seconds())
print 'Part2   Speedup is %.4f' % (speedup2,)


def warp(lsrtime):
    """ Convert the LSR Time to our workshop time, of some sort"""
    base = orig0 if lsrtime < origB else origB
    newbase = workshop0 if lsrtime < origB else workshopB2
    _speedup = speedup1 if lsrtime < origB else speedup2
    return newbase + datetime.timedelta(
                seconds=((lsrtime - base).total_seconds() / _speedup))
# ______________________________________________________________________

# Get me a client, stat
spr_client = util.get_spreadsheet_client(util.get_config())

feed = spr_client.get_list_feed("1V6-xV7Sm3ST-0tYpvtD5s-sMmNe_FdhKDCrVS5vOxoE",
                                "od6")


def getdir(u, v):
    if v == 0:
        v = 0.000000001
    dd = math.atan(u / v)
    ddir = (dd * 180.00) / math.pi

    if (u > 0 and v > 0):  # First Quad
        ddir = 180 + ddir
    elif (u > 0 and v < 0):  # Second Quad
        ddir = 360 + ddir
    elif (u < 0 and v < 0):  # Third Quad
        ddir = ddir
    elif (u < 0 and v > 0):  # Fourth Quad
        ddir = 180 + ddir

    return int(math.fabs(ddir))

lkp = {'HAIL': 'H',
       'TORNADO': 'T',
       'TSTM WND GST': 'G',
       'WIND': 'G',
       'TSTM WND DMG': 'D',
       'TSTM WND DMG': 'D',
       'NON-TSTM WND DMG': 'O',
       'NON-TSTM WND GST': 'N',
       'FUNNEL CLOUD': 'C',
       'HEAVY RAIN': 'R',
       'FLASH FLOOD': 'F',
       'FLOOD': 'F',
       'WALL CLOUD': 'X',
       'LIGHTNING': 'L'}

lsrtime = orig0

for entry in feed.entry:
    data = entry.to_dict()
    # Since data is CST -6, we simply need to add 6 hours
    ts = datetime.datetime.strptime(data['obstimecst'], '%m/%d/%Y %H:%M:%S')
    ts += datetime.timedelta(hours=6)
    lsrtime = orig0.replace(year=ts.year, month=ts.month, day=ts.day,
                            hour=ts.hour, minute=ts.minute)
    newts = warp(lsrtime)
    newtstamp = newts.strftime('%m/%d/%Y %H:%M:%S')
    entry.set_value('workshoputc', newtstamp)
    spr_client.update(entry)
    sql = """select name, ST_Distance(ST_Transform(
        ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'),26915), 
        ST_Transform(the_geom,26915)),
        ST_x(ST_Transform(ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'),26915)) - ST_x(ST_Transform(the_geom,26915)),
        ST_y(ST_Transform(ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'),26915)) - ST_y(ST_Transform(the_geom,26915))
        from cities_iowa 
        ORDER by st_distance ASC LIMIT 1""" % (data['lon'], data['lat'],
                                               data['lon'], data['lat'],
                                               data['lon'], data['lat'])
    """
    mcursor.execute(sql)
    row2 = mcursor.fetchone()
    # print row2
    deg = getdir(0 - row2[2], 0 - row2[3])
    drct = pyiemutil.drct2text(deg)
    miles = row2[1] * 0.0006214  # meters -> miles
    newcity = "%.1f %s %s" % (miles, drct, row2[0])
    if data['workshopcity'] != newcity:
        print '%s -> %s' % (data['workshopcity'], newcity)
        entry.set_value('workshopcity', newcity)
        spr_client.update(entry)
        print 'Updated'
    continue
    #print ts, newts, delta
    """
    geo = 'SRID=4326;POINT(%s %s)' % (data['lon'], data['lat'])
    sql = """INSERT into lsrs (valid, display_valid, type, magnitude, city, source,
    remark, typetext, geom, wfo) values (%s, %s, %s, %s, %s, %s,
    %s, %s, %s, 'DMX')"""
    args = (newts, newts,
            lkp[data['type']], data['magnitude'],
            data['workshopcity'], data['source'], data['remark'],
            data['type'], geo)
    print lsrtime, newts
    mcursor.execute(sql, args)

mcursor.close()
mydb.commit()
