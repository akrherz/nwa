<?php
/* Generate GR placefile of LSRs */
date_default_timezone_set('America/Chicago');
$conn = pg_connect("dbname=nwa host=127.0.0.1");

if (isset($_REQUEST["all"])){
  $rs = pg_query($conn, "SELECT *, ST_x(geom) as lon, ST_y(geom) as lat 
      from lsrs WHERE valid > '1999-04-01' and valid < '1999-05-01' ORDER  by valid ASC ");
  $title = "Local Storm Reports - ALL";
} else {
  $rs = pg_query($conn, "SELECT *, ST_x(geom) as lon, ST_y(geom) as lat 
      from lsrs WHERE valid > (now() - '20 minutes'::interval) and
      valid < (now() - '120 seconds'::interval)");
  $title = "Local Storm Reports";
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
  $ts = strtotime($row["valid"]);
  $q = sprintf("%s %s %s\\n%s\\n%s", $row["magnitude"], $row["typetext"], date("h:i A", $ts), $row["city"], substr($row["remark"],0,256) );
  $icon = $ltypes[$row["type"]];
  echo sprintf("Object: %.4f,%.4f
  Threshold: 999
  Icon: 0,0,%s,1,%s,\"%s\"
END:\n", $row['lat'], $row['lon'], $d, $icon, $q);
}

?>
