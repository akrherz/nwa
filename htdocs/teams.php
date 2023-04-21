<html>
<head>
<meta http-equiv="refresh" content="15">
</head>
<body>
<h3>Teams With [Number of Valid Warnings] between 2:30 and 4 PM</h3>

<?php
$conn = pg_connect("dbname=nwa");

echo "<table border='1' cellpadding='6' cellspacing='0'>";
$rs = pg_query($conn, "SELECT team, count(*) from nwa_warnings ".
        "where issue >= '2023-04-20 19:30+00' and obs is not null ".
        " and issue < '2023-04-20 21:00+00' ".
        " GROUP by team ORDER by team ASC");
$total = 0;
for ($i=0;$row = pg_fetch_array($rs);$i++)
{
    $total += $row["count"];
   if ($i % 3 == 0){ echo "<tr>"; }
   $uri = sprintf("/auto/teamwarns_%s.png", urlencode($row["team"]));
   $html = sprintf(
       '<a href="%s">%s [%s]</a>', $uri, $row["team"], $row["count"],
   );
   echo sprintf("<td>%s [%s]</td>", $row["team"], $row["count"]);
   // echo sprintf("<td>%s</td>", $html);
   if (($i + 1) % 3 == 0){ echo "</tr>"; }
}
echo "</table>";
echo sprintf("<h3>All yall have issued %s warnings!</h3>", $total);
