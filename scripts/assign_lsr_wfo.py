"""Make sure that the LSRs are actually for DMX!"""
import sys

import psycopg2

pgconn = psycopg2.connect(database="nwa")
cursor = pgconn.cursor()
wcursor = pgconn.cursor()
pgconn2 = psycopg2.connect(database="postgis")
cursor2 = pgconn2.cursor()

cursor.execute(
    """
    SELECT ST_x(geom), ST_y(geom), wfo, valid, city from lsrs
    where valid > 'TODAY'
"""
)
for row in cursor:
    lon = row[0]
    lat = row[1]
    wfo = row[2]
    valid = row[3]
    city = row[4]
    cursor2.execute(
        """
        SELECT wfo from ugcs WHERE
   ST_transform(ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'),4326) && geom
   and ST_Contains(geom,
           ST_transform(ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'),4326))
           and end_ts is null and substr(ugc, 3, 1) = 'C'
   """
        % (lon, lat, lon, lat)
    )
    row2 = cursor2.fetchone()
    if row2[0] == wfo:
        continue
    print("Updating wfo from %s to %s" % (wfo, row2[0]))
    wcursor.execute(
        """
    UPDATE lsrs SET wfo = %s where city = %s
    and valid = %s
    """,
        (row2[0], city, valid),
    )
    if wcursor.rowcount == 0:
        print(row)
        sys.exit()

wcursor.close()
pgconn.commit()
pgconn.close()
