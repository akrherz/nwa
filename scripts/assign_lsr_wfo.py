"""Make sure that the LSRs are actually for DMX!"""
import psycopg2

pgconn = psycopg2.connect(database="nwa")
cursor = pgconn.cursor()
wcursor = pgconn.cursor()
pgconn2 = psycopg2.connect(database="postgis")
cursor2 = pgconn2.cursor()

cursor.execute(
    """
    SELECT ST_x(geom), ST_y(geom), oid, wfo from lsrs
    where valid > 'TODAY'
"""
)
for row in cursor:
    oid = row[2]
    wfo = row[3]
    lon = row[0]
    lat = row[1]
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
    UPDATE lsrs SET wfo = %s where oid = %s
    """,
        (row2[0], oid),
    )

wcursor.close()
pgconn.commit()
pgconn.close()
