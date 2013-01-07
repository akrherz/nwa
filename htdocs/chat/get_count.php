<?php
$i = -1;
$data = file('json-chat.txt');
foreach($data as $line){
    $i++;
}
echo $i;
?>
