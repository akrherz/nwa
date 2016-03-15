<?php
//date_default_timezone_set('America/Chicago');
date_default_timezone_set('UTC');

include("../include/cow.php");
$conn = pg_connect("dbname=nwa host=127.0.0.1");
pg_query($conn, "SET TIME ZONE 'UTC'");
/* Get list of teams */
$rs = pg_query($conn, "SELECT distinct team from nwa_warnings 
		WHERE issue >= '2015-04-02 19:30'");
$results = Array();
//$results["KICT ACTUAL"] = Array(
// "warnings" => 17,
// "csi" => 0.42,
// "pod" => 0.60,
// "far" => 0.41,
// "av" => 37,
// "sz" => 1420,
// "lincoln" => 37.0 * 0.42,
//);

for($i=0;$row=@pg_fetch_array($rs,$i);$i++)
{
  $cow = new cow($conn);
  $cow->setLimitWFO( Array($row["team"]) );
  $cow->setLimitTime( mktime(19,30,0,4,2,2015), mktime(21,0,0,4,2,2015) ); //!GMT
  $cow->setHailSize( 1.00 );
  $cow->setLimitType( Array('SV','TO') );
  $cow->setLimitLSRType( Array('SV','TO') );
  $cow->setLSRBuffer( 15 );
  $cow->milk();
  
  $results[ $row["team"] ] = Array(
     "warnings" =>  sizeof($cow->warnings),
     "csi" =>  $cow->computeCSI(),
  		"tecount" => $cow->tecount,
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
<link rel="stylesheet" type="text/css" href="/ext-3.4.1/resources/css/ext-all.css"/>
<script type="text/javascript" src="/ext-3.4.1/adapter/ext/ext-base.js"></script>
<script type="text/javascript" src="/ext-3.4.1/ext-all.js"></script>
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
<span style="font-size: 48;"> &nbsp; &nbsp; http://192.168.10.201/cow.php</span><br />

<button id="create-grid" type="button">Interactive Grid</button>
<table border="1" cellpadding="2" cellspacing="0" id="datagrid" width="800">
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
<th>TE Count</th>
</tr>
</thead>
<tbody>
<?php
while (list($k,$v) = each($results)){
  echo sprintf("<tr><td>%s</td><td>%02d</td><td>%05.2f</td><td>%04.2f</td><td>%04d</td><td>%05.2f</td><td>%04.2f</td><td>%04.2f</td><td>%02d</td></tr>", $k, $v["warnings"], $v["lincoln"], $v["csi"], $v["sz"], $v["av"], $v["pod"], $v["far"], $v["tecount"]);
}
?>
</tbody>
</table>

<p><br />&nbsp;
<p><img src="iemcow.jpg" align="left" /><h1>IEM COW, Moooooooo!</h1>

</body>
</html>
