<html>
<head>
<meta http-equiv="refresh" content="15">
</head>
<body>
<h3>Teams With 1+ Warning</h3>
<?php
$conn = pg_connect("dbname=nwa host=127.0.0.1");

echo "<table border='1' cellpadding='6' cellspacing='0'>";
$rs = pg_query($conn, "SELECT distinct(team) from nwa_warnings "
		."where issue > 'TODAY' and obs is not null ORDER by team ASC");
for ($i=0;$row= @pg_fetch_array($rs,$i);$i++)
{
   if ($i % 5 == 0){ echo "<tr>"; }
   echo sprintf("<td>%s</td>", $row["team"]);
   if (($i + 1) % 5 == 0){ echo "</tr>"; }
}
echo "</table>";
?>
