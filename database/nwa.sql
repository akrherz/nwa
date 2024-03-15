--- NWA Database Tables
create extension postgis;

CREATE TABLE lsrs (
    valid timestamp with time zone,
    type character(1),
    magnitude real,
    city character varying(32),
    county character varying(32),
    state character(2),
    source character varying(32),
    remark text,
    wfo character(3),
    typetext character varying(40),
    geom geometry,
    display_valid timestamptz,
    CONSTRAINT enforce_dims_geom CHECK ((st_ndims(geom) = 2)),
    CONSTRAINT enforce_geotype_geom CHECK (((geometrytype(geom) = 'POINT'::text) OR (geom IS NULL))),
    CONSTRAINT enforce_srid_geom CHECK ((st_srid(geom) = 4326))
);
grant select on lsrs to apache;


ALTER TABLE public.lsrs OWNER TO akrherz;

CREATE TABLE nwa_warnings (
    id integer NOT NULL,
    issue timestamp with time zone,
    expire timestamp with time zone,
    updated timestamp with time zone,
    type character(3),
    gtype character(1),
    wfo character(3),
    eventid smallint,
    status character(3),
    fips integer,
    fcster character varying(24),
    report text,
    svs text,
    ugc character varying(6),
    phenomena character(2),
    significance character(1),
    hvtec_nwsli character(5),
    geom geometry,
    emergency boolean,
    team character varying,
    ibwtag text,
    client_addr text,
    CONSTRAINT enforce_dims_geom CHECK ((st_ndims(geom) = 2)),
    CONSTRAINT enforce_geotype_geom CHECK (((geometrytype(geom) = 'MULTIPOLYGON'::text) OR (geom IS NULL))),
    CONSTRAINT enforce_srid_geom CHECK ((st_srid(geom) = 4326))
);
grant all on nwa_warnings to apache;


ALTER TABLE public.nwa_warnings OWNER TO akrherz;

