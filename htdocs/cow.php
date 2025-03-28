<?php
//date_default_timezone_set('America/Chicago');
date_default_timezone_set('UTC');
require_once "../include/config.php";
require_once "../include/cow.php";
$config = load_config();
$conn = pg_connect("dbname=nwa host=127.0.0.1");
pg_query($conn, "SET TIME ZONE 'UTC'");
/* Get list of teams */
$stname = uniqid();
pg_prepare(
    $conn,
    $stname,
    "SELECT distinct team from nwa_warnings WHERE " .
        "issue >= $1 and issue < $2 ".
        "and team != 'THE_WEATHER_BUREAU2'"
);
$rs = pg_execute(
    $conn,
    $stname,
    array(
        $config["timing"]["workshop_begin"]->format("Y-m-d H:i:s"),
        $config["timing"]["workshop_end"]->format("Y-m-d H:i:s")
    )
);
$results = array();
$tor_results = array();

for ($i = 0; $row = pg_fetch_array($rs); $i++) {
    $cow = new cow($conn);
    $cow->setLimitWFO(array($row["team"]));
    $cow->setForecastWFO("DMX");
    $cow->setLimitTime(
        $config["timing"]["workshop_begin"],
        $config["timing"]["workshop_end"]);
    $cow->setHailSize(1);
    $cow->setLimitType(array('SV', 'TO'));
    $cow->setLimitLSRType(array('SV', 'TO'));
    $cow->setLSRBuffer(15);
    $cow->milk();

    $results[$row["team"]] = array(
        "warnings" =>  sizeof($cow->warnings),
        "csi" =>  $cow->computeCSI(),
        "tecount" => $cow->tecount,
        "missed" => $cow->computeUnwarnedEvents(),
        "pod" =>  $cow->computePOD(),
        "far" =>  $cow->computeFAR(),
        "av" =>  $cow->computeAreaVerify(),
        "sz" =>  $cow->computeAverageSize(),
        "lincoln" =>  $cow->computeAreaVerify() * $cow->computeCSI(),
    );

    $cow = new cow($conn);
    $cow->setLimitWFO(array($row["team"]));
    $cow->setLimitTime($config["timing"]["workshop_begin"], $config["timing"]["workshop_end"]);
    $cow->setHailSize(1);
    $cow->setLimitType(array('TO'));
    $cow->setLimitLSRType(array('TO'));
    $cow->setLSRBuffer(15);
    $cow->milk();

    $tor_results[$row["team"]] = array(
        "warnings" =>  sizeof($cow->warnings),
        "csi" =>  $cow->computeCSI(),
        "tecount" => $cow->tecount,
        "missed" => $cow->computeUnwarnedEvents(),
        "pod" =>  $cow->computePOD(),
        "far" =>  $cow->computeFAR(),
        "av" =>  $cow->computeAreaVerify(),
        "sz" =>  $cow->computeAverageSize(),
        "lincoln" =>  $cow->computeAreaVerify() * $cow->computeCSI(),
    );

    /*
  reset($cow->lsrs);
  while (list($k, $v) = each($cow->lsrs)){
      if (! $v["warned"]){
          echo sprintf("%s %s %s %s %s</br>", $v["tdq"], date("Y/m/d H:i", $v["ts"]),
                  $v["remark"], $v["city"], $v["county"]);
      }
  }
  */
}

?>
<html>

<head>
    <link rel="stylesheet" type="text/css" href="/vendor/ext/3.4.1/resources/css/ext-all.css" />
    <script type="text/javascript" src="/vendor/ext/3.4.1/adapter/ext/ext-base.js"></script>
    <script type="text/javascript" src="/vendor/ext/3.4.1/ext-all.js"></script>
    <script type="text/javascript" src="TableGrid.js"></script>
    <script>
        Ext.onReady(function() {
            var btn = Ext.get("create-grid");
            btn.on("click", function() {
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

            var btn2 = Ext.get("create-grid2");
            btn2.on("click", function() {
                btn2.dom.disabled = true;

                // create the grid
                var grid = new Ext.ux.grid.TableGrid("datagrid2", {
                    stripeRows: true // stripe alternate rows
                });
                grid.render();
            }, false, {
                single: true
            }); // run once
            btn2.dom.disabled = false; // For page reload support?
        });
    </script>


</head>

<body style="margin: 5px !important;">
    <span style="font-size: 48;"> &nbsp; &nbsp; https://workshop.agron.iastate.edu/cow.php</span><br />

    <span style="font-size: 30;">Tornado and Severe Thunderstorm</span>

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
                <th>Missed LSRs</th>
            </tr>
        </thead>
        <tbody>
            <?php
            foreach ($results as $k => $v) {
                $uri = sprintf("/auto/teamwarns_%s.png", urlencode($k));
                echo sprintf(
                    "<tr><td><a href=\"%s\">%s</a></td><td>%02d</td><td>%05.2f</td><td>%04.2f</td>" .
                        "<td>%04d</td><td>%05.2f</td><td>%04.2f</td><td>%04.2f</td>" .
                        "<td>%02d</td><td>%02d</td></tr>",
                    $uri, $k,
                    $v["warnings"],
                    $v["lincoln"],
                    $v["csi"],
                    $v["sz"],
                    $v["av"],
                    $v["pod"],
                    $v["far"],
                    $v["tecount"],
                    $v['missed']
                );
            }
            ?>
        </tbody>
    </table>

    <hr />
    <span style="font-size: 30;">Just Tornado</span>

    <button id="create-grid2" type="button">Interactive Grid</button>
    <table border="1" cellpadding="2" cellspacing="0" id="datagrid2" width="800">
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
                <th>Missed LSRs</th>
            </tr>
        </thead>
        <tbody>
            <?php
            foreach ($tor_results as $k => $v) {
                //$uri = sprintf("/auto/teamwarns_%s.png", $k);
                $uri = sprintf("disabled");
                echo sprintf(
                    "<tr><td><a href=\"%s\">%s</a></td><td>%02d</td><td>%05.2f</td><td>%04.2f</td>" .
                        "<td>%04d</td><td>%05.2f</td><td>%04.2f</td><td>%04.2f</td>" .
                        "<td>%02d</td><td>%02d</td></tr>",
                    $uri, $k,
                    $v["warnings"],
                    $v["lincoln"],
                    $v["csi"],
                    $v["sz"],
                    $v["av"],
                    $v["pod"],
                    $v["far"],
                    $v["tecount"],
                    $v['missed']
                );
            }
            ?>
        </tbody>
    </table>

    <p><br />&nbsp;
    <p><img src="iemcow.jpg" align="left" />
    <h1>IEM COW, Moooooooo!</h1>

</body>

</html>
