<?php

class TuneC
{

    public $config;
    public $project;
    public $pcfg;
    public $connection;
    public $session;
    public $hgCommand;
    public $localWorkingDir;
    private $stampfile = 'tunec_stamp';

    public function __construct($project)
    {
        $this->project = $project;
        $this->config = self::getConfig();
        $this->pcfg = $this->config['project'][$this->project];
        $this->hgCommand = $this->config['hg_command'];
        $this->localWorkingDir = $this->pcfg['local']['dir'] . $this->pcfg['local']['vendor_dir'];
    }

    /**
     * Check status
     */
    public function checkStatus()
    {
        $this->hgAddRemove();
        $this->hgCommit();
        $localStatus = $this->checkLocalRepo();
        $localSummary = $this->getLocalSummary();
        $remoteSummary = $this->getRemoteSummary();
        echo "Last update peformed at: " . $remoteSummary['date'] . " (" . self::time_elapsed_string($remoteSummary['date'], true) . ")\n";
        echo "Remote checksum/rev : " . $remoteSummary['no'] . ':' . $remoteSummary['revision'] . "\n";
        echo "Local checksum/rev  : " . $localSummary['no'] . ':' . $localSummary['revision'] . "\n";
        if ($localStatus && ($localSummary['revision'] == $remoteSummary['revision'])) {

        } else {
            echo "\nThe local vendor folder has changed since the last update. Remote project may need an update.\n\n";
        }
    }

    /**
     * Push local checnges to remote location
     */
    public function pushChanges()
    {
        $this->commitLocalChanges();
        $localSummary = $this->getLocalSummary();
        $remoteSummary = $this->getRemoteSummary();
        if (($localSummary['no'] == $remoteSummary['no']) && ($localSummary['revision'] == $remoteSummary['revision'])) {
            echo "\nIt looks like no update is required.\n";
            echo 'The remote directoy was updated at: ' . $remoteSummary['date'] . ' (rev ' . $remoteSummary['no'] . ':' . $remoteSummary['revision'] . ')' . "\n";
            echo "No update actions were performed!\n\n";
            die();
        }
        if ($localSummary['no'] < $remoteSummary['no']) {
            echo "\nHmmm... something is wrong. The remote location seems to be newer than the local!\n";
            echo "Sorry, you need to solve this problem by yourself.\n\n";
            die();
        }
        $changes = $this->getLocalChangesSince($remoteSummary['revision']);
        $this->uploadFiles($changes['M']);
        $this->uploadFiles($changes['A']);
        $this->removeRemoteFiles($changes['R']);
        $this->updateRemoteStamp($localSummary['no'] . ':' . $localSummary['revision']);
    }

    /**
     * Init local repo
     */
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

    /**
     * Init remote locatio, uploads local files
     */
    public function initRemote()
    {
        $repoOk = $this->checkLocalRepo();
        if (!$repoOk) {
            die("\nLocal vendor dir is changed!\n\n");
        }
        if (false && !$this->remoteCheckDir($this->pcfg['remote']['vendor_dir'])) {
            echo "\nCreating remote dir (" . $this->pcfg['remote']['vendor_dir'] . ")\n";
            $p = $this->remoteMakeDir($this->pcfg['remote']['vendor_dir']);
            if ($p) {
                echo "Success.\n";
            } else {
                die("Failed!");
            }
        }
        $files = $this->getLocalRepoFiles();
        $this->prepareRemoteDirs($files);
        $this->uploadFiles($files);
        $localRevision = $this->getLocalRevision();
        $this->updateRemoteStamp($localRevision);
    }

    public function removeRemoteFiles($files)
    {
        foreach ($files as $file) {
            echo "Removing " . $file . "\n";
            $this->remoteDeleteFile($this->pcfg['remote']['vendor_dir'] . $file);
        }
    }

    public function getLocalChangesSince($revison, $tillRev = 'tip')
    {
        $changedFiles = $this->hgStatusRev($revison, $tillRev);
        $changes = [
            'A' => [],
            'R' => [],
            'M' => [],
        ];
        foreach ($changedFiles as $change) {
            preg_match("/([ARM])\ (.+)/", $change, $m);
            $changes[$m[1]][] = $m[2];
        }
        return $changes;
    }

    public function hgStatusRev($revision, $tillRev = 'tip')
    {
        $p = $this->hg('status --rev ' . $revision . ':' . $tillRev);
        $list = self::text2lines($p);
        return $list;
    }

    /**
     *
     */
    public function getLocalSummary()
    {
        $summaryLines = $this->hgSummary();
        foreach ($summaryLines as $line) {
            preg_match("/^parent\:\ ([0-9]+)\:([a-z0-9]+)/", $line, $m);
            if (count($m) > 0) {
                $status['no'] = $m[1];
                $status['revision'] = $m[2];
            }
        }
        return $status;
    }

    public function commitLocalChanges()
    {
        $this->hgAddRemove();
        $this->hgCommit();
    }

    /**
     *
     * @return array
     */
    public function hgSummary()
    {
        $p = $this->hg('summary');
        $summary = self::text2lines($p);
        return $summary;
    }

    public function hgAddRemove()
    {
        return $this->hg('addremove');
    }

    public function hgCommit($comment = false)
    {
        if (!$comment) {
            $comment = 'tunec' . date('Y-m-d H:i:s');
        }
        return $this->hg('commit -m "' . $comment . '"');
    }

    public function hgAddAll()
    {
        return $this->hg('add *');
    }

    public function hgRemoveFiles($files)
    {
        chdir($this->localWorkingDir);
        foreach ($files as $file) {
            shell_exec($this->hgCommand . ' remove "' . $file . '"');
        }
    }

    public function hgAddFiles($files)
    {
        chdir($this->localWorkingDir);
        foreach ($files as $file) {
            shell_exec($this->hgCommand . ' add "' . $file . '"');
        }
    }

    public function getHgUntrackedFiles()
    {
        $p = $this->hg('status -un');
        $files = self::text2lines($p);
        return $files;
    }

    public function getHgDeletedFiles()
    {
        $p = $this->hg('status -dn');
        $files = self::text2lines($p);
        return $files;
    }

    public function manageLocalVendorAdditions()
    {
        $newFiles = $this->getNewFiles();
        var_dump($newFiles);
    }

    public function manageLocalVendorDeletions()
    {
        $delFiles = $this->getDeletedFiles();
        var_dump($delFiles);
    }

    public function getDeletedFiles()
    {
        chdir($this->localWorkingDir);
        $p = shell_exec($this->hgCommand . ' status -d');
        return self::text2lines($p);
    }

    public function getRemoteSummary()
    {
        $tempfile = tempnam('.', '.remotestamp_');
        $this->remoteGetFile($this->pcfg['remote']['vendor_dir'] . $this->stampfile, $tempfile);
        $remoteStamp = json_decode(file_get_contents($tempfile), true);
        unlink($tempfile);
        return $remoteStamp;
    }

    public function updateRemoteStamp($revision)
    {
        $revArray = preg_split("/\:/", $revision);
        $stamp = [
            'no' => $revArray[0],
            'revision' => $revArray[1],
            'date' => date('Y-m-d H:i:s')
        ];
        $stampJson = json_encode($stamp);
        $tempfile = tempnam(".", '.tunec_');
        file_put_contents($tempfile, $stampJson);
        echo "Uploading stamp file.\n";
        $this->remotePutFile($tempfile, $this->pcfg['remote']['vendor_dir'] . $this->stampfile);
        unlink($tempfile);
    }

    public function getLocalRevision()
    {
        $p = $this->hg('summary');
        preg_match("/parent\:\ (.*)\ tip/", $p, $m);
        return $m[1];
    }

    public function hg($command)
    {
        chdir($this->localWorkingDir);
        $result = shell_exec($this->hgCommand . ' ' . $command);
        return $result;
    }

    public function uploadFiles($files)
    {
        foreach ($files as $file) {
            $localFileFullPath = $this->pcfg['local']['dir'] . $this->pcfg['local']['vendor_dir'] . $file;
            $remoteFileFullPath = $this->pcfg['remote']['vendor_dir'] . $file;
            $this->checkRemotePath(self::getPath($remoteFileFullPath), true);
            echo "Uploading " . $remoteFileFullPath . "\n";
            $this->remotePutFile($localFileFullPath, $remoteFileFullPath);
        }
    }

    public function checkRemotePath($path, $createDir = false)
    {
        $pathStatus = $this->remoteCheckDir($path);
        if ($pathStatus) {
            return true;
        } else {
            $parrent = self::getPath($path, true);
            if ($this->checkRemotePath($parrent, $createDir)) {
                echo "Create $path\n";
                $this->remoteMakeDir($path);
                return true;
            };
        }
        return false;
    }

    public static function getPath($file, $useDirsAsFiles = false)
    {
        $filename = basename($file);
        if ($useDirsAsFiles) {
            $path = preg_replace("/$filename([\/]?)$/", "", $file);
        } else {
            $path = preg_replace("/$filename$/", "", $file);
        }
        return $path;
    }

    public function prepareRemoteDirs($files)
    {
        $dirs = $this->getFileDirs($files);
        foreach ($dirs as $dir) {
            $this->remoteMakeDir($this->pcfg['remote']['vendor_dir'] . $dir);
        }
    }

    public function getFileDirs($files, $base = '')
    {
        $dirs = [];
        foreach ($files as $file) {
            $parts = preg_split("#/#", $file);
            array_pop($parts);
            if ($parts) {
                $dirs[] = join("/", $parts) . "/";
            }
        }
        sort($dirs);
        $dirs = array_unique($dirs);
        return $dirs;
    }

    public function getLocalRepoFiles()
    {
        $hg = $this->config['hg_command'];
        $localVendorDir = $this->pcfg['local']['dir'] . $this->pcfg['local']['vendor_dir'];
        chdir($localVendorDir);
        $p = shell_exec($hg . ' status --all');
        $lines = self::text2lines($p);
        $files = [];
        foreach ($lines as $key => $line) {
            preg_match("/^C\ (.*)/", $line, $m);
            if (count($m) > 1) {
                $files[] = $m[1];
            }
        }
        return $files;
    }

    public function getLocalRepoDirs()
    {
        $files = $this->getLocalRepoFiles();
    }

    public function checkLocalRepo()
    {
        $hg = $this->config['hg_command'];
        $localVendorDir = $this->pcfg['local']['dir'] . $this->pcfg['local']['vendor_dir'];
        chdir($localVendorDir);
        $p = shell_exec($hg . ' status');
        if ($p === null) {
            return true;
        }
        return false;
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
                $this->connection = $connection;
                $this->session = ssh2_sftp($connection);
                break;
            case 'ftp':
                $connection = $this->ftp_connection();
                $this->connection = $connection;
                $this->session = true;
                break;
            default:
                $connection = false;
        }
        return $connection;
    }

    public function sftp_connection()
    {
        if (key_exists('password', $this->pcfg['sftp'])) {
            $connection = ssh2_connect($this->pcfg['sftp']['host'], $this->pcfg['sftp']['port']);
            try {
                echo "Connecting...";
                if (ssh2_auth_password($connection, $this->pcfg['sftp']['username'], $this->pcfg['sftp']['password'])) {
                    echo "success!\n";
                    return $connection;
                } else {
                    throw new Exception('Authentication Failed!');
                }
            } catch (Exception $e) {
                error_log("Exception: " . $e->getMessage());
                die();
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

    public function ftp_connection()
    {
        if (key_exists('password', $this->pcfg['ftp'])) {
            $connection = ftp_connect($this->pcfg['ftp']['host'], $this->pcfg['ftp']['port']);
            try {
                echo "Connecting...";
                if (ftp_login($connection, $this->pcfg['ftp']['username'], $this->pcfg['ftp']['password'])) {
                    echo "success!\n";
                    return $connection;
                } else {
                    throw new Exception('Authentication Failed!');
                }
            } catch (Exception $e) {
                error_log("Exception: " . $e->getMessage());
                die();
            }
        } else {
            die('Please provide pubkey or password!');
        }
        return $connection;
    }

    public function remotePutFile($localFile, $remoteFile)
    {
        $this->connect();
        try {
            switch ($this->pcfg['connection_type']) {
                case 'sftp':
                    if (ssh2_scp_send($this->connection, $remoteFile, $localFile)) {
                        return true;
                    }
                    break;
                case 'ftp':
                    if (ftp_put($this->connection, $remoteFile, $localFile)) {
                        return true;
                    }
                    break;
            }
            throw new Exception("Can not upload " . $remoteFile);
        } catch (Exception $e) {
            error_log("Exception: " . $e->getMessage());
            die();
        }
    }

    public function remoteGetFile($remoteFile, $localFile)
    {
        $this->connect();
        try {
            switch ($this->pcfg['connection_type']) {
                case 'sftp':
                    if (ssh2_scp_recv($this->connection, $remoteFile, $localFile)) {
                        return true;
                    };
                    break;
                case 'ftp':
                    if (ftp_get($this->connection, $localFile, $remoteFile)) {
                        return true;
                    };
                    break;
                default:
            }
            throw new Exception("Can not download " . $remoteFile);
        } catch (Exception $e) {
            error_log("Exception: " . $e->getMessage());
        }
        return false;
    }

    public function remoteCheckDir($directory)
    {
        $this->connect();
        switch ($this->pcfg['connection_type']) {
            case 'sftp':
                $statinfo = @ssh2_sftp_stat($this->session, $directory);
                break;
            case 'ftp':
                $statinfo = is_dir('ftp://' .$this->pcfg['ftp']['username'] .':'. $this->pcfg['ftp']['password'] . '@' . $this->pcfg['ftp']['host'] . $directory);
                break;
            default:
        }
        if ($statinfo) {
            return true;
        } else {
            return false;
        };
    }

    public function remoteMakeDir($directory, $recursive = true)
    {
        $this->connect();
        try {
            switch ($this->pcfg['connection_type']) {
                case 'sftp':
                    if (ssh2_sftp_mkdir($this->session, $directory)) {
                        return true;
                    };
                    break;
                case 'ftp':
                    if($this->remoteCheckDir($directory)){
                        return true;
                    }else{
                        $parrent = self::getPath($directory, true);
                        if($parrent == "/"){
                            throw new Exception("Can not make dir!");
                        }
                        $this->remoteMakeDir($parrent);
                    }
                    if (ftp_mkdir($this->connection, $directory)) {
                        return true;
                    };
                    break;
                default:
            }
            throw new Exception("Can not make directory " . $directory);
        } catch (Exception $e) {
            error_log("Exception: " . $e->getMessage());
            die();
        }
        return false;
    }

    public function remoteDeleteFile($file)
    {
        $this->connect();
        try {
            switch ($this->pcfg['connection_type']) {
                case 'sftp':
                    if (ssh2_sftp_unlink($this->session, $file)) {
                        return true;
                    };
                    break;
                case 'ftp':
                    if (ftp_delete($this->connection, $file)) {
                        return true;
                    };
                    break;
                default:
            }
            throw new Exception("Can not delete " . $file);
        } catch (Exception $e) {
            error_log("Exception: " . $e->getMessage());
        }
        return false;
    }

    private static function text2lines($text, $keepEmtpy = false)
    {
        $lines = preg_split("/((\r?\n)|(\r\n?))/", $text);
        if (!$keepEmtpy) {
            foreach ($lines as $key => $line) {
                if ($line == "") {
                    unset($lines[$key]);
                }
            }
        }
        return $lines;
    }

    public static function time_elapsed_string($datetime, $full = false)
    {
        $now = new DateTime;
        $ago = new DateTime($datetime);
        $diff = $now->diff($ago);

        $diff->w = floor($diff->d / 7);
        $diff->d -= $diff->w * 7;

        $string = array(
            'y' => 'year',
            'm' => 'month',
            'w' => 'week',
            'd' => 'day',
            'h' => 'hour',
            'i' => 'minute',
            's' => 'second',
        );
        foreach ($string as $k => &$v) {
            if ($diff->$k) {
                $v = $diff->$k . ' ' . $v . ($diff->$k > 1 ? 's' : '');
            } else {
                unset($string[$k]);
            }
        }

        if (!$full)
            $string = array_slice($string, 0, 1);
        return $string ? implode(', ', $string) . ' ago' : 'just now';
    }

    public function test()
    {
        $p = $this->remoteCheckDir('/test/vendor/1/');
        var_dump($p);
        echo "test\n";
        die();
    }
}
