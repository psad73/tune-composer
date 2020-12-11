<?php

require 'vendor/autoload.php';
require 'TuneC.class.php';

if (count($argv) < 2) {
    echo "Usage: \n";
    die("At least provide the project name!\n\n");
}

$project = $argv[1];
if($argc > 2){
    $command = strtolower($argv[2]);
}else{
    $command = 'help';
}

$tuneC = new TuneC($project);

switch($command){
    case 'initlocal':
        $tuneC->initLocal();
        break;
    case 'initremote':
        $tuneC->initRemote();
        break;
    case 'push':
        $tuneC->push();
        break;
    case 'status':
        break;
    case 'test':
        $tuneC->test();
        break;
    case 'showconfig':
        $tuneC->showConfig();
        break;
    case 'help':
    default:
        printHelp();
}

function printHelp(){
    echo "\n";
    echo "tunec <project name> <command>\n";
    echo "commands:\n";
    echo "\tinitlocal - \n";
    echo "\tinitremote - \n";
    echo "\tinitpush - \n";
}