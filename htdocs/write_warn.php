<?php
/*
 * Ingest a warning from WarnGen
 * CHANGE ME!,1,SVR,2010/03/07 04:17:27,2010/03/07 04:28:33,42.159832,-94.208847,42.466557,-94.431694,42.782372,-93.794228,42.247829,-93.534668,,,,,,
 */
date_default_timezone_set('America/Chicago');
$conn = pg_connect("dbname=nwa host=127.0.0.1");
pg_query($conn, "SET TIME ZONE 'UTC'");
$rs = pg_prepare($conn, "INSERT", "INSERT into nwa_warnings(team, eventid,
      issue, expire, geom, phenomena, wfo, gtype, emergency, obs) VALUES 
      ($1, $2, $3, $4, $5, $6, 'DMX', 'P', $7, $8)");

$data = isset($_REQUEST["obs"]) ? $_REQUEST["obs"] : die("APIFAIL");

$tokens = split(",", $data);

$siteID = $tokens[0];
$warnID = $tokens[1];
$warnType = substr($tokens[2],0,2);
$sts = strtotime($tokens[3]);
$ets = strtotime($tokens[4]);
$geom = "SRID=4326;MULTIPOLYGON(((";
for($i=5;$i<sizeof($tokens);$i=$i+2)
{
  $lat = @$tokens[$i];
  $lon = @$tokens[$i+1];
  if ($lat != "" && $lon != ""){
    $geom .= sprintf("%s %s, ", $lon, $lat);
  }
}
$geom .= sprintf("%s %s)))", $tokens[6], $tokens[5]);

pg_execute($conn, "INSERT", array($siteID, $warnID, date("Y-m-d H:i", $sts),
          date("Y-m-d H:i", $ets), $geom, $warnType, 
		($tokens[2] == 'TOR_EM') ? 't': 'f', $data));

?>
