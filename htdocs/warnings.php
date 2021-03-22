<?php
$grversion = isset($_GET['version']) ? floatval($_GET["version"]): 1.0;
$conn = pg_connect("dbname=nwa host=127.0.0.1");

function compute_color($row){
    // Figure out the color to be used for plotting, from Washoe 18 Mar 2021
    if ($row["phenomena"] == "TO"){
        if ($row["emergency"] == "t"){
            return "128 0 255";
        }
        if ($row["ibwtag"] == "Catastrophic"){
            return "255 0 255";
        }
        return "255 0 0";
    } elseif ($row["phenomena"] == "SV"){
        if ($row["ibwtag"] == "Destructive"){
            return "255 128 0";
        }
        return "255 255 0";
    }
    return "0 0 0";
}


header("Content-type: text/plain");

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
} else if (isset($_GET["tor"])){
  echo "Threshold: 999
  Title: All TOR Warnings
  Refresh: 1
  ";
    $rs = pg_query($conn, "SELECT ST_astext(geom) as t, *,
    to_char(issue at time zone 'UTC', 'YYYY-MM-DDThh24:MI:SSZ') as iso_issue,
    to_char(expire at time zone 'UTC', 'YYYY-MM-DDThh24:MI:SSZ') as iso_expire
    from nwa_warnings 
    WHERE phenomena = 'TO' and expire > now() and issue < now()
      and team != 'THE_WEATHER_BUREAU'");  
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
for ($i=0;$row=pg_fetch_array($rs);$i++)
{
  $meat = str_replace("MULTIPOLYGON(((", "", $row["t"]);
  $meat = str_replace(")))", "", $meat);
  $segments = explode("),(", $meat);
  echo "Color: ". compute_color($row)  ."\n";
  if ($grversion >= 1.5 && ! isset($_REQUEST["bureau"])){
  	echo sprintf("TimeRange: %s %s\n", $row["iso_issue"], $row["iso_expire"]);
  }
  foreach($segments as $q => $seg)
  {
    echo "Line: 3, 0, ". $row["team"] ."\n";
    $tokens = explode(",", $seg);
    foreach($tokens as $p => $s){
      $t = explode(" ", $s);
      echo sprintf("  %.5f,%.5f", $t[1], $t[0]) ."\n";
    }
    echo "End:\n";
  }

}

?>
