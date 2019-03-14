<html>
<head>
<meta http-equiv="refresh" content="15">
</head>
<body>
<h3>Teams With [Number of Valid Warnings] since 1930 UTC</h3>
<?php
$conn = pg_connect("dbname=nwa host=127.0.0.1");

echo "<table border='1' cellpadding='6' cellspacing='0'>";
$rs = pg_query($conn, "SELECT team, count(*) from nwa_warnings "
		."where issue >= '2018-04-24 19:30+00' and obs is not null ".
		" and issue < '2018-04-24 21:00+00' ".
		" GROUP by team ORDER by team ASC");
$total = 0;
for ($i=0;$row= @pg_fetch_array($rs,$i);$i++)
{
	$total += $row["count"];
   if ($i % 5 == 0){ echo "<tr>"; }
   echo sprintf("<td>%s [%s]</td>", $row["team"], $row["count"]);
   if (($i + 1) % 5 == 0){ echo "</tr>"; }
}
echo "</table>";
echo sprintf("<h3>All yall have issued %s warnings!</h3>", $total);
?>
