"""Pull what's available on an online Google Spreadsheet into our local DB"""
from __future__ import print_function
import datetime

import psycopg2
import pytz
import pyiem.cscap_utils as util

SHEET = "1VZmRgcXNZhGdpkkYmNwUhSsLNzrN_JlZhUI-zT3SPAk"

def convtime(val):
    """Convert time"""
    try:
        return datetime.datetime.strptime(val, '%m/%d/%Y %H:%M:%S')
    except ValueError:
        return datetime.datetime.strptime(val, '%Y-%m-%d %H:%M')


def main():
    """Go Main Go"""
    mydb = psycopg2.connect('dbname=nwa')
    mcursor = mydb.cursor()
    mcursor.execute("""DELETE from lsrs where date(valid) = '2018-03-22'""")
    print('Deleted %s rows' % (mcursor.rowcount,))

    # Get me a client, stat
    spr_client = util.get_spreadsheet_client(util.get_config())

    feed = spr_client.get_list_feed(SHEET, "od6")

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
                lkp[data['type']],
                0 if data['magnitude'] == 'None' else data['magnitude'],
                data['workshopcity'], data['source'], data['remark'],
                data['type'], geo)
        mcursor.execute(sql, args)
        inserts += 1

    mcursor.close()
    mydb.commit()
    print("Inserted %s new entries!" % (inserts,))
    print(("ALERT: Consider running assign_lsr_wfo.py to get WFO right in DB"))


if __name__ == '__main__':
    main()
