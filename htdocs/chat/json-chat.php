<?php
date_default_timezone_set('GMT');
putenv("TZ=UTC");

$user = isset($_GET["user"]) ? $_GET["user"] : "M2";
$seqnum = isset($_GET["seqnum"]) ? $_GET["seqnum"] : "0";
$said = isset($_GET["said"]) ? $_GET["said"] : "";
$new_seq = $seqnum + 1;
$tony = "Tony";
$chris = "Chris";
$bruce = "Bruce";
$cathy = "Cathy";
$tim = "Tim";
$carl = "Carl";
$probe = "Probe";
$m1 = "M1";
$m2 = "M2";
$m3 = "M3";
$mt = "MT";
$count = 1;


header( 'Content-type: text/plain');

if (isset($_GET["said"])){
 $data = file("json-chat.txt");
 foreach($data as $line){
   $txt = explode("|",trim($line));
   $count = $txt[0] + 1;
 }
 $fh = fopen("json-chat.txt", 'a');
 $now = date('Y-m-d H:i:s');
 $new_chat = "".$count."|".$now."|".$user."|".htmlspecialchars($_GET["said"])."";
 fwrite($fh, "$new_chat\n");
 fclose($fh);
}

echo "{\"lsrs\":[";
$linewant = $seqnum;
$data = file("json-chat.txt");
$i = 0;
$j = 0;
foreach($data as $line){
    $txt = explode("|",trim($line));   
    $short_time = explode(" ", $txt[1]);
    $c_num = $txt[0];
    if($txt[0] <= 9){
         $c_num = "00".$txt[0]."";
    }
    elseif($txt[0] <= 99){
         $c_num = "0".$txt[0]."";
    }
    $shorter_time = explode(":",$short_time[1]);
    $s_time = "".$c_num."-".$shorter_time[0].":".$shorter_time[1]."z";
    $get_t = strtotime("$txt[1]");
    $h = date('H');
    if($h < 9){
    $bound = strtotime(date('Y-m-d 09:00:00')) - 86400;
    }
    if($h >= 9){
          $bound = strtotime(date('Y-m-d 09:00:00'));
    }
    $diff = $get_t - $bound;
    if($diff < 86400 && $diff > 0){
         $i += 1;
    }
    if ($i > $linewant) {
          if($diff < 86400 && $diff > 0){
               $j++;
               if($txt[2] ==  $m1 || $txt[2] == $bruce || $txt[2] == $cathy){
                    $color = "FF0000";
               } 
               elseif($txt[2] ==  $m2 || $txt[2] == $chris){
                    $color = "0000CC";
               }
               elseif($txt[2] ==  $m3 || $txt[2] == $tony){
                    $color = "009900";
               }
               elseif($txt[2] ==  $mt || $txt[2] == $tim || $txt[2] == $carl || $txt[2] == $probe){
                    $color = "FF6600";
               }
               else{
                    $color = "000000";
               }

               if($j == 1){
                    echo "{\"seqnum\":\"".$i."\",\"valid\":\"".$s_time."\",\"user\":\"<font color=".$color."><b><u>".$txt[2]."</b></u></font>\",\"remark\":\"<font color=".$color.">".$txt[3]."</font>\"}";
               }
               else{
                    echo ",{\"seqnum\":\"".$i."\",\"valid\":\"".$s_time."\",\"user\":\"<font color=".$color."><b><u>".$txt[2]."</b></u></font>\",\"remark\":\"<font color=".$color.">".$txt[3]."</font>\"}";
               }
          }
     }
}
echo "]}";

?>
