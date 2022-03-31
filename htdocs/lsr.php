<?php
/* Generate GR placefile of LSRs */
$grversion = isset($_GET['version']) ? floatval($_GET["version"]): 1.0;
date_default_timezone_set('America/Chicago');
$conn = pg_connect("dbname=nwa host=127.0.0.1");

if (isset($_REQUEST["all"])){
  $rs = pg_query($conn, "SELECT *, ST_x(geom) as lon, ST_y(geom) as lat, ".
  	"to_char((valid + '60 minutes'::interval) at time zone 'UTC', 'YYYY-MM-DDThh24:MI:SSZ') as iso_end, ".
    "to_char(valid at time zone 'UTC', 'YYYY-MM-DDThh24:MI:SSZ') as iso_begin ".
    "from lsrs WHERE valid > '2022-03-31' and valid < '2022-04-01' ".
  	"ORDER  by valid ASC ");
  $title = "Local Storm Reports - ALL Today";
} else {
	// Note that display_valid is used here!
  $rs = pg_query($conn, "SELECT *, ST_x(geom) as lon, ST_y(geom) as lat, ".
  	"to_char((valid + '60 minutes'::interval) at time zone 'UTC', 'YYYY-MM-DDThh24:MI:SSZ') as iso_end, ".
    "to_char(valid at time zone 'UTC', 'YYYY-MM-DDThh24:MI:SSZ') as iso_begin ".
    "from lsrs WHERE display_valid > (now() - '60 minutes'::interval) and ".
    "display_valid < (now() - '0 seconds'::interval)");
  $title = "Local Storm Reports Past 60mins";
}

header("Content-type: text/plain");
echo "Refresh: 1
Threshold: 999
Title: ${title}
IconFile: 1, 20, 20, 10, 10, \"lsricons.png\"
Font: 1, 11, 1, \"Courier New\"
";

$ltypes = Array(
 "0"=> 20,
 "1"=> 20,
 "2"=> 15,
 "3"=> 15,
 "4"=> 15,
 "5"=> 13,
 "6"=> 4,
 "7"=> 4,
 "8"=> 15,
 "9"=> 15,
 "a"=> 15,
 "A"=> 1,
 "B"=> 5,
 "C"=> 10,
 "D"=> 22,
 "E"=> 7,
 "F"=> 7,
 "G"=> 1,
 "H"=> 11,
 "I"=> 14,
 "J"=> 15,
 "K"=> 15,
 "L"=> 15,
 "M"=> 1,
 "N"=> 1,
 "O"=> 1,
 "P"=> 15,
 "Q"=> 20,
 "R"=> 12,
 "s"=> 16,
 "S"=> 16,
 "T"=> 19,
 "U"=> 15,
 "V"=> 15,
 "W"=> 18,
 "X"=> 19,
 "Z"=> 3,
);

for ($i=0;$row=@pg_fetch_assoc($rs,$i);$i++)
{
  $d = 0;
  $ts = new DateTime($row["valid"]);
  $q = sprintf("%s %s %s\\n%s\\n%s", $row["magnitude"], $row["typetext"], 
  $ts->format("h:i A"), $row["city"], substr($row["remark"],0,256) );
  $icon = $ltypes[$row["type"]];
  $tr = '';
  if ($grversion >= 1.5 && ! isset($_REQUEST["all"])){
  	$tr = sprintf("TimeRange: %s %s\n", $row["iso_begin"], $row["iso_end"]);
  }
  echo sprintf("\nObject: %.4f,%.4f\n".
  "Threshold: 999\n".
  "%s".
  "Icon: 0,0,%s,1,%s,\"%s\"\n".
  "END:\n", $row['lat'], $row['lon'], $tr, $d, $icon, $q);
}

?>
