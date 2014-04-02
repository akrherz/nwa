<html>
<head>
</head>
<body>
<h3>Teams With 1+ Warning</h3>
<?php
$conn = pg_connect("dbname=nwa");

echo "<table border='1' cellpadding='6'>";
$rs = pg_query($conn, "SELECT distinct(team) from nwa_warnings where issue > 'TODAY' ORDER by team ASC");
for ($i=0;$row= @pg_fetch_array($rs,$i);$i++)
{
   if ($i % 3 == 0){ echo "<tr>"; }
   echo sprintf("<td>%s</td>", $row["team"]);
   if (($i + 1) % 3 == 0){ echo "</tr>"; }
}
echo "</table>";
?>
