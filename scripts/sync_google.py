import psycopg2
mydb = psycopg2.connect('dbname=nwa')
mcursor = mydb.cursor()

mcursor.execute("""DELETE from lsrs where valid > '2013-02-12'""")
print 'Deleted %s rows' % (mcursor.rowcount,)

import sys
sys.path.insert(0, "/home/akrherz/projects/iem/scripts/cscap")
import util
import datetime
import ConfigParser
config = ConfigParser.ConfigParser()
config.read('/home/akrherz/projects/iem/scripts/cscap/mytokens.cfg')

# Shifting
time00 = datetime.datetime(2013,2,12,20,30)
time01 = datetime.datetime(2013,2,25,20,21)

time10 = datetime.datetime(2013,2,12,22,0)
time11 = datetime.datetime(2013,2,25,22,0)

speedup = (time11 - time01).seconds / float((time10 - time00).seconds)
print 'Speedup is %.4f' % (speedup,)


# Get me a client, stat
spr_client = util.get_spreadsheet_client(config)

feed = spr_client.get_list_feed("0AqZGw0coobCxdFByVl9NYzhWSTI3Uk1hRmJ4S2Z0VGc",
                                "od6")

lkp = {'HAIL': 'H',
       'TORNADO': 'T',
       'TSTM WND GST': 'G',
       'TSTM WND DMG': 'D',
       'NON-TSTM WND DMG': 'O',
       'NON-TSTM WND GST': 'N',
       'FUNNEL CLOUD': 'C'}

for entry in feed.entry:
    data = entry.to_dict()
    #print data
    ts = datetime.datetime.strptime(data['validgmt'], '%m/%d/%Y %H:%M:%S')
    if ts >= time10:
        delta = (ts - time10).seconds / speedup
        newts = time11 + datetime.timedelta(seconds=delta)
    else:
        delta = (time10 - ts).seconds / speedup
        newts = time11 - datetime.timedelta(seconds=delta)
    newtstamp = newts.strftime('%m/%d/%Y %H:%M:%S')
    entry.set_value('dryrun2time', newtstamp)
    spr_client.update(entry) 
    print ts, newts, delta
    geo = 'SRID=4326;POINT(%s %s)' % (data['lon'], data['lat'])
    sql = """INSERT into lsrs (valid, type, magnitude, city, source,
    remark, typetext, geom) values (%s, %s, %s, %s, %s,
    %s, %s, %s)""" 
    args = (newts.strftime("%Y-%m-%d %H:%M+00"),
                lkp[ data['type']], data['magnitude'],
                data['city'], data['source'], data['remark'],
                data['type'], geo)
    mcursor.execute(sql, args)

mcursor.close()
mydb.commit()
