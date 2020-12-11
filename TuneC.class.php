<?php

class TuneC
{

    public $config;
    public $project;
    public $pcfg;
    public $connection;
    public $session;

    public function __construct($project)
    {
        $this->project = $project;
        $this->config = self::getConfig();
        $this->pcfg = $this->config['project'][$this->project];

        //var_dump($this->pcfg);
    }

    public function test()
    {
        echo "test\n";
        var_dump($this->project);
        var_dump($this->config);
    }

    public function initRemote()
    {
        $repoOk = $this->checkLocalRepo();
        if(!$repoOk){
            die("\nLocal vendor dir is changed!\n\n");
        }
        if (false && !$this->checkRemoteDir($this->pcfg['remote']['vendor_dir'])) {
            echo "\nCreating remote dir (" . $this->pcfg['remote']['vendor_dir'] . ")\n";
            $p = ssh2_sftp_mkdir($this->session, $this->pcfg['remote']['vendor_dir']);
            if($p){
                echo "Success.\n";
            }else{
                die ("Failed!");
            }
        }
        $localVendorDir = $this->pcfg['local']['dir'] . $this->pcfg['local']['vendor_dir'];
        $localFiles = scandir($localVendorDir);
        var_dump($localFiles);
    }

    public function checkLocalRepo(){
        $hg = $this->config['hg_command'];
        $localVendorDir = $this->pcfg['local']['dir'] . $this->pcfg['local']['vendor_dir'];
        chdir($localVendorDir);
        $p = shell_exec($hg . ' status');
        if($p === null){
            return true;
        }
        return false;
    }

    public function initLocal()
    {
        $hg = $this->config['hg_command'];
        $localVendorDir = $this->pcfg['local']['dir'] . $this->pcfg['local']['vendor_dir'];
        if (!is_readable($localVendorDir) || !is_dir($localVendorDir)) {
            die("vendor dir is missing in local project!\n");
        }
        if (is_readable($localVendorDir . '.hg')) {
            die("HG dir already exists!\n");
        }
        chdir($localVendorDir);
        // hg init
        shell_exec($hg . ' init');
        // hg add
        $p = shell_exec($hg . ' add');
        echo "HG add\n";
        echo $p . "\n";
        //hg commit
        $p = shell_exec($hg . ' commit -m "init"');
        echo "HG commit\n" . $p . "\n";
    }

    public function checkRemoteDir($file)
    {
        $this->connect();
        $statinfo = ssh2_sftp_stat($this->session, $file);
        if ($statinfo) {
            return true;
        } else {
            return false;
        };
    }

    public function makeRemoteDir($dir)
    {

    }

    public static function getConfig()
    {
        $config = yaml_parse_file('tunec.yaml');
        return $config;
    }

    public function connect()
    {

        if ($this->session) {
            return $this->connection;
        }

        switch ($this->pcfg['connection_type']) {
            case 'sftp':
                $connection = $this->sftp_connection();
                break;
            default:
                $connection = false;
        }
        $this->connection = $connection;
        $this->session = ssh2_sftp($connection);
        return $connection;
    }

    public function sftp_connection()
    {
        if (key_exists('password', $this->pcfg['sftp'])) {
            $connection = ssh2_connect($this->pcfg['sftp']['host'], $this->pcfg['sftp']['port']);
            if (ssh2_auth_password($connection, $this->pcfg['sftp']['username'], $this->pcfg['sftp']['password'])) {
                echo "Authentication Successful!\n";
                return $connection;
            } else {
                die('Authentication Failed...');
            }
        } elseif (key_exists('pubkey', $this->pcfg['sftp']) && is_readable($this->pcfg['sftp']['pubkey'])) {
            if (ssh2_auth_pubkey_file($connection,
                    $this->pcfg['sftp']['username'],
                    $this->pcfg['sftp']['pubkey'],
                    $this->pcfg['sftp']['privkey'])) {
                echo "Public Key Authentication Successful\n";
                return $connection;
            } else {
                die('Public Key Authentication Failed');
            }
        } else {
            die('Please provide pubkey or password!');
        }
        return $connection;
    }
}
