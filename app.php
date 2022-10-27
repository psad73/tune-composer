<?php
require __DIR__ .'/src/Tunec/Tunec.php';

use Tunec\Tunec;

if (count($argv) < 2) {
    echo "Usage: \n";
    die("At least provide the project name!\n\n");
}

$project = $argv[1];
if ($argc > 2) {
    $command = strtolower($argv[2]);
} else {
    $command = 'help';
}

$tuneC = new Tunec($project);

switch ($command) {
    case 'status':
    case 'checkstatus':
    case 'check':
        $tuneC->checkStatus();
        break;
    case 'initlocal':
        $tuneC->initLocal();
        break;
    case 'initremote':
        $tuneC->initRemote();
        break;
    case 'push':
        $tuneC->pushChanges();
        break;
    case 'showconfig':
        $tuneC->showConfig();
        break;
    case 'help':
    default:
        printHelp();
}

function printHelp()
{
    echo "\n";
    echo "tunec <project name> <command>\n";
    echo "commands:\n";
    echo "\tshowconfig - list configuration\n";
    echo "\tcheckstatus - check local and remote status\n";
    echo "\tinitlocal - init local vendor dir\n";
    echo "\tinitremote - init remote location\n";
    echo "\tpush - push local changes to remote\n";

}
