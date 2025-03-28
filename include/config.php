<?php

function load_config() {
    $configpath = dirname(__FILE__) . '/../config/workshop.json';
    $data = json_decode(file_get_contents($configpath), true);
    $data["timing"]["archive_begin"] = DateTime::createFromFormat(
        "Y-m-d\\TH:i:s\\Z",
        $data["timing"]["archive_begin"],
        new DateTimeZone("UTC")
    );
    $data["timing"]["archive_end"] = DateTime::createFromFormat(
        "Y-m-d\\TH:i:s\\Z",
        $data["timing"]["archive_end"],
        new DateTimeZone("UTC")
    );
    $data["timing"]["workshop_begin"] = DateTime::createFromFormat(
        "Y-m-d\\TH:i:s\\Z",
        $data["timing"]["workshop_begin"],
        new DateTimeZone("UTC")
    );
    $data["timing"]["workshop_end"] = DateTime::createFromFormat(
        "Y-m-d\\TH:i:s\\Z",
        $data["timing"]["workshop_end"],
        new DateTimeZone("UTC")
    );
    return $data;
}