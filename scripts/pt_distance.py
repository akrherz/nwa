import re
from pyIEM import iemdb
import pg
postgis = pg.connect('nwa')

data = {}

rs = postgis.query("""
SELECT team, ST_asText(geom) as txt
from nwa_warnings WHERE 
 issue >= '2011-03-31 14:10'
"""  ).dictresult()

for i in range(len(rs)):
  if not data.has_key(rs[i]['team']):
    data[rs[i]['team']] = {'count': 0, 'hits': 0}
  # Find our points
  tokens = re.findall("([\-0-9\.]+) ([0-9\.]+)", rs[i]['txt'])
  for pr in tokens[:-1]:
    rs2 = postgis.query("""
select min(ST_distance(ST_Transform(ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'),
  2163), ST_Transform(exteriorring(geometryn(geom,1)),2163) )) from nws_ugc WHERE wfo = '%s'
    """ % (pr[0], pr[1], 'DMX') ).dictresult()
    if rs2[0]['min'] < 2000.:
      data[rs[i]['team']]['hits'] += 1
    data[rs[i]['team']]['count'] += 1

for wfo in data.keys():
  print '%s,%s,%s,%.3f' % (wfo, data[wfo]['hits'], data[wfo]['count'],
    float(data[wfo]['hits'])/float(data[wfo]['count'])*100.)
