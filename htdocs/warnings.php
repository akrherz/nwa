<?php
$grversion = isset($_GET['version']) ? floatval($_GET["version"]): 1.0;
$conn = pg_connect("dbname=nwa host=127.0.0.1");

header("Content-type: text/plain");

$colors = Array(
   "SV" => "255 255 0",
   "TO" => "255 0 0",
    3 => "152 152 152",
    7 => "152 152 152",
    11 => "152 152 152",
    15 => "255 197 197",
    19 => "254 51 153",
    23 => "181 0 181",
    27 => "255 197 197",
    31 => "254 51 153",
    35 => "181 0 181",
    39 => "153 255 255",
    43 => "0 153 254",
    47 => "0 0 158",
    51 => "232 95 1",
    56 => "255 197 197",
    60 => "254 51 153",
    64 => "181 0 181",
    86 => "125 0 0");

if (isset($_GET["bureau"])){
	echo "Threshold: 999
Title: Actual Bureau Warnings
Refresh: 1
";
	$rs = pg_query($conn, "SELECT ST_astext(geom) as t, *,
	to_char(issue at time zone 'UTC', 'YYYY-MM-DDThh24:MI:SSZ') as iso_issue,
	to_char(expire at time zone 'UTC', 'YYYY-MM-DDThh24:MI:SSZ') as iso_expire
 	from nwa_warnings
	WHERE expire > now() and issue < now() and team = 'THE_WEATHER_BUREAU'");
} else{
echo "Threshold: 999
Title: All Warnings
Refresh: 1
";
	$rs = pg_query($conn, "SELECT ST_astext(geom) as t, *,
	to_char(issue at time zone 'UTC', 'YYYY-MM-DDThh24:MI:SSZ') as iso_issue,
	to_char(expire at time zone 'UTC', 'YYYY-MM-DDThh24:MI:SSZ') as iso_expire
	from nwa_warnings 
	WHERE  expire > now() and issue < now()
    and team != 'THE_WEATHER_BUREAU'");
}
for ($i=0;$row= @pg_fetch_array($rs,$i);$i++)
{
  $meat = str_replace("MULTIPOLYGON(((", "", $row["t"]);
  $meat = str_replace(")))", "", $meat);
  $segments = explode("),(", $meat);
  if ($row["emergency"] == 't'){ 
  	echo "Color: 85	26	139\n";
  } else{
  	echo "Color: ".$colors[$row["phenomena"]]  ."\n";
  }
  if ($grversion >= 1.5 && ! isset($_REQUEST["bureau"])){
  	echo sprintf("TimeRange: %s %s\n", $row["iso_issue"], $row["iso_expire"]);
  }
  while(list($q,$seg) = each($segments))
  {
    echo "Line: 3, 0, ". $row["team"] ."\n";
    $tokens = explode(",", $seg);
    while (list($p,$s) = each($tokens)){
      $t = explode(" ", $s);
      echo sprintf("  %.5f,%.5f", $t[1], $t[0]) ."\n";
    }
    echo "End:\n";
  }

}

?>
