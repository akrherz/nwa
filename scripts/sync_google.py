"""Pull what's available on an online Google Spreadsheet into our local DB"""

import psycopg2
import pyiem.cscap_utils as util
import datetime
import pytz

mydb = psycopg2.connect('dbname=nwa')
mcursor = mydb.cursor()
mcursor.execute("""DELETE from lsrs where valid > '2017-03-30'""")
print 'Deleted %s rows' % (mcursor.rowcount,)

# Get me a client, stat
spr_client = util.get_spreadsheet_client(util.get_config())

feed = spr_client.get_list_feed("1WlJsuSPzf1_Mlx-sHjkB6woWyU1_REpsvmBYSUOmuzE",
                                "od6")

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


def convtime(val):
    try:
        return datetime.datetime.strptime(val, '%m/%d/%Y %H:%M:%S')
    except ValueError:
        return datetime.datetime.strptime(val, '%Y-%m-%d %H:%M')


inserts = 0
for entry in feed.entry:
    data = entry.to_dict()
    ts = convtime(data['workshoputc'])
    ts = ts.replace(tzinfo=pytz.utc)
    if data['workshoprevealutc'] is None:
        revealts = ts
    else:
        revealts = convtime(data['workshoprevealutc'])
        revealts = revealts.replace(tzinfo=pytz.utc)
    if ts != revealts:
        print(("  Entry has reveal delta of %s minutes"
               ) % ((revealts - ts).total_seconds() / 60.,))
    geo = 'SRID=4326;POINT(%s %s)' % (data['lon'], data['lat'])
    sql = """
    INSERT into lsrs (valid, display_valid, type, magnitude, city, source,
    remark, typetext, geom, wfo) values (%s, %s, %s, %s, %s, %s,
    %s, %s, %s, 'DMX')"""
    args = (ts, revealts,
            lkp[data['type']], data['magnitude'],
            data['workshopcity'], data['source'], data['remark'],
            data['type'], geo)
    mcursor.execute(sql, args)
    inserts += 1

mcursor.close()
mydb.commit()
print("Inserted %s new entries!" % (inserts,))
