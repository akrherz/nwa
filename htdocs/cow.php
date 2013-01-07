<?php
//date_default_timezone_set('America/Chicago');
date_default_timezone_set('GMT');

include("../include/cow.php");
$conn = pg_connect("dbname=nwa");
/* Get list of teams */
$rs = pg_query($conn, "SELECT distinct team from nwa_warnings WHERE issue >= '2011-03-31 14:10'");
$results = Array();
$results["NWS Topeka"] = Array(
 "warnings" => 20,
 "csi" => 0.44,
 "pod" => 0.70,
 "far" => 0.35,
 "av" => 22,
 "sz" => 2063,
 "lincoln" => 22 * 0.44,
);
$results["NWS Omaha"] = Array(
 "warnings" => 21,
 "csi" => 0.36,
 "pod" => 0.86,
 "far" => 0.62,
 "av" => 15,
 "sz" => 1545,
 "lincoln" => 15 * 0.36,
);
for($i=0;$row=@pg_fetch_array($rs,$i);$i++)
{
  $cow = new cow($conn);
  $cow->setLimitWFO( Array($row["team"]) );
  $cow->setLimitTime( mktime(19,10,0,3,31,2011), mktime(22,40,0,3,31,2011) ); //!GMT
  $cow->setHailSize( 0.75 );
  $cow->setLimitType( Array('SV','TO') );
  $cow->setLimitLSRType( Array('SV','TO') );
  $cow->setLSRBuffer( 15 );
  $cow->milk();

  $results[ $row["team"] ] = Array(
     "warnings" =>  sizeof($cow->warnings),
     "csi" =>  $cow->computeCSI(),
     "pod" =>  $cow->computePOD(),
     "far" =>  $cow->computeFAR(),
     "av" =>  $cow->computeAreaVerify(),
     "sz" =>  $cow->computeAverageSize(),
     "lincoln" =>  $cow->computeAreaVerify() * $cow->computeCSI(),
  );
}

?>
<html>
<head>
<link rel="stylesheet" type="text/css" href="ext-3.3.1/resources/css/ext-all.css"/>
<script type="text/javascript" src="ext-3.3.1/adapter/ext/ext-base.js"></script>
<script type="text/javascript" src="ext-3.3.1/ext-all.js"></script>
<script type="text/javascript" src="TableGrid.js"></script>
<script>
Ext.onReady(function(){
    var btn = Ext.get("create-grid");
    btn.on("click", function(){
        btn.dom.disabled = true;
        
        // create the grid
        var grid = new Ext.ux.grid.TableGrid("datagrid", {
            stripeRows: true // stripe alternate rows
        });
        grid.render();
    }, false, {
        single: true
    }); // run once
    btn.dom.disabled = false; // For page reload support?
});
</script>


</head>
<body>
<button id="create-grid" type="button">Interactive Grid</button>
<table border="1" cellpadding="2" cellspacing="0" id="datagrid" width="600">
<thead>
<tr>
 <th>Team</th>
<th>Warnings</th>
<th>CSI * AreaVerify</th>
 <th>CSI</th>
<th>Size (sq km)</th>
<th>Area Verify %</th>
<th>POD</th>
<th>FAR</th>
</tr>
</thead>
<tbody>
<?php
while (list($k,$v) = each($results)){
  echo sprintf("<tr><td>%s</td><td>%s</td><td>%05.2f</td><td>%04.2f</td><td>%04d</td><td>%05.2f</td><td>%04.2f</td><td>%04.2f</td></tr>", $k, $v["warnings"], $v["lincoln"], $v["csi"], $v["sz"], $v["av"], $v["pod"], $v["far"]);
}
?>
</tbody>
</table>

<p><br />&nbsp;
<p><img src="iemcow.jpg" align="left" /><h1>IEM COW, Moooooooo!</h1>
</body>
</html>
