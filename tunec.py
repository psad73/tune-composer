#!/usr/bin/python
import os
import sys
import re
import json
import tarfile
import tempfile
import requests
import urllib.parse
from urllib.parse import urlparse
from configparser import ConfigParser
from ftplib import FTP
from datetime import datetime

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class message:
    def getTD(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    def iWarning(self):
        return (self.getTD() + bcolors().WARNING + " WARNING: " + bcolors().ENDC)
    def iError(self):
        return (self.getTD() + bcolors().FAIL + " ERROR: " + bcolors().ENDC)
    def iOk(self):
        return (self.getTD() + bcolors().OKGREEN + " OK: " + bcolors().ENDC)        
    def iInfo(self):
        return (self.getTD() + bcolors().OKBLUE + " INFO: " + bcolors().ENDC)        
    def iDebug(self):
        return (self.getTD() + bcolors().OKCYAN + " DEBUG: " + bcolors().ENDC)        


class ComposerSync:
    configFile = '.tunec.cfg'
    config = {
        "url": "ftp://ftp.example.net:21/public_html",
        "user": "ftp-user",
        "password": "secr3t",
        "public-web-url": "",
    }
    ftp = ''
    tempRemoteComposerLockFile = 'composer.remote.lock'


    archiveTempFile = ''
    phpTempFile = ''
    apiToken = ''

    packagesToRemove = []
    packagesToUpdate = []
    packagesToUpload = []

    def __init__(self):
        # self.loadConfig()
        # self.getRemoteConnection()
        return

    def getDefaultConfig(self):
        config = ConfigParser()
        config.add_section('remote')
        config.set('remote', 'url', 'ftp.myproject.com')
        config.set('remote', 'user', 'user')
        config.set('remote', 'password', 'password')
        config.set('remote', 'remote-root', '/var/www/html/')
        config.set('remote', 'public-web-url', 'https://myproject.com/')
        config.set('remote', 'public-web-path', '/var/www/html/public/')
        config.set('remote', 'php-vendor-root', '/var/www/html/public/')
        return config

    ################
    #
    # loadConfig
    #
    #
    def loadConfig(self):
        configObj = ConfigParser()
        if (os.path.isfile(self.configFile)):
            configObj.read(self.configFile)
            self.config = configObj
        else:
            gitConfigObj = ConfigParser()
            gitConfigObj.read(".git/config")
            if (not ('git-ftp' in gitConfigObj.sections())):
                print(
                    "You don't have a [git-ftp] in your .git/config nor a .tunec.conf file?! Not good...")
                user_input = input("Create a default .tune.cfg file (y/n)?: ")
                if user_input.lower() == 'y':
                    makeConfig(false)
                exit()
            self.config = ConfigParser()
            self.config.add_section('remote')
            for key in dict(gitConfigObj['git-ftp']).keys():
                if (key == 'url'):
                    parsed_uri = urlparse(gitConfigObj['git-ftp'][key])
                    host = parsed_uri.netloc
                    self.config.set('remote', 'host', host)
                self.config.set('remote', key, gitConfigObj['git-ftp'][key])
            if ('public-web-url' in gitConfigObj['git-ftp']):
                self.config.set('remote', 'public-web-url',
                                gitConfigObj['git-ftp']['public-web-url'])
            else:
                publicaccessurl = 'http://' + \
                    urllib.parse.urlparse(
                        self.config['remote']['url']).netloc + '/'
                self.config.set('remote', 'public-web-url', publicaccessurl)

    ###
    #
    # makeConfig
    #
    #
    def makeConfig(self):
        overWrite = True
        if (os.path.isfile(self.configFile)):
            user_input = input(
                f"{self.configFile} exists. Overwrite? (yes/no): ")
            if user_input.lower() == 'yes':
                overWrite = True
            else:
                overWrite = False
        if (overWrite):
            config = self.getDefaultConfig()
            print(config['remote']['url'])
            section = 'remote'
            with open(self.configFile, 'w') as configfile:
                configfile.write("[remote]\n")
                for key in config[section]:
                    line = "{} = {}".format(key, config[section][key])
                    print(line)                    
                    configfile.write(line)
                    configfile.write("\n")
        return True

    def getLocalPackages(self):
        f = open('composer.lock')
        localComposer = json.load(f)
        return localComposer

    def getRemotePackages(self):
        temporaryRemoteComposerFile = self.tempRemoteComposerLockFile
        ftp = self.getRemoteConnection()
        ftp.cwd(self.config['remote']['remote-root'])        
        with open(temporaryRemoteComposerFile, 'wb') as fp:
            ftp.retrbinary('RETR composer.lock', fp.write)
        f = open(temporaryRemoteComposerFile)        
        remoteComposer = json.load(f)
        return remoteComposer

    def remove_ftp_dir(self, ftp, path):
        for (name, properties) in ftp.mlsd(path=path):
            if name in ['.', '..']:
                continue
            elif properties['type'] == 'file':
                ftp.delete(f"{path}/{name}")
            elif properties['type'] == 'dir':
                self.remove_ftp_dir(ftp, f"{path}/{name}")
        ftp.rmd(path)

    def getRemoteConnection(self):
        ftp = FTP(self.config['remote']['url'])
        ftp.login(user=self.config['remote']['user'],
                  passwd=self.config['remote']['password'])        
        self.ftp = ftp
        return ftp

    ###
    #
    # REMOVE packages
    #
    def removeRemotePackage(self, package):
        ftp = self.getRemoteConnection()
        print("removing: {}".format(package['name']))
        try:
            self.remove_ftp_dir(ftp, 'vendor/' + package['name'])
        except:
            print(message().iWarning(), end='')
            print("Problem removing remote {}".format(package['name']))
        else:
            print(message().iOk(), end='')
            print("Package {} removed".format(package['name']))
    ###
    #
    #
    #
    def removeRemotePackages(self):
        packages = self.packagesToRemove
        for package in packages:
            self.removeRemotePackage(package)

    def makeArchive(self, items):
        print(message().iInfo() + f"Creating archive for {items}")
        for key, path in enumerate(items):
            if(not os.path.exists(path)):                               
                print(message().iWarning() + f"Skipping '{path}' while making achive! Item does not exists, or is not accessible. So...")                
                items.pop(key)
                print(message().iInfo() + f"Creating archive for {items}") 
              
        tarfilename = "tunec_" + next(tempfile._get_candidate_names()) + ".tar.gz"
        self.archiveTempFile = tarfilename
        tar = tarfile.open(tarfilename, mode='w:gz')
        for entry in items:
            tar.add(entry)
        tar.close()
        print(message().iOk() + f"Created archive {tarfilename}")
        print()
        return tarfilename

    def uploadFile(self, file, destFolder):        
        print(message().iInfo() + f"Uploading {file} to remote {destFolder} ...") #, end="")
        fh = open(file, 'rb')
        if(destFolder):
            try:
                self.ftp.cwd(destFolder)
            except Exception as e:                
                sys.exit(f"ERROR: Check remote dirs in config. Is '{destFolder}' a correct folder? [{str(e)}]")
        try:
            result = self.ftp.storbinary(f"STOR {file}", fh)
        except Exception as e:
            print(message().iError(), end='')
            print(result)
            sys.exit()
        print(message().iOk(), end='')
        print(result)
        print()
        fh.close()
        return result
    
    def makePhpExtractScript(self, apitoken = False):
        secret = "tunec_" + next(tempfile._get_candidate_names())
        phpfilename = secret + ".php"
        self.phpTempFile = phpfilename
        if(not apitoken):
            apitoken = next(tempfile._get_candidate_names())            
            self.apiToken = apitoken
        archivefile = self.config['remote']['php-vendor-root'].strip("/")  +  "/" + self.archiveTempFile.strip("/")
        destExtractFolder = self.config['remote']['php-vendor-root'].strip("/") + "/"

        phpfile = open(phpfilename, 'w')
        phpFileFtp = f"{self.config['remote']['public-web-path']}{phpfilename}"
        print(message().iDebug() + f"token:{apitoken}")
        phpfile.write(
            f"<?php if(filter_input(INPUT_SERVER,'HTTP_X_API_TOKEN')!='{apitoken}'){{header($_SERVER[\"SERVER_PROTOCOL\"].' 500 Internal Server Error',true,500);die('wrong token');}};try{{$phar=new PharData('{archivefile}');}}catch(Exception $e){{header($_SERVER[\"SERVER_PROTOCOL\"].' 500 Internal Server Error',true,500);echo $e->getMessage();die();}};try{{$phar->extractTo('{destExtractFolder}',null,true);}}catch(Exception $e){{header($_SERVER[\"SERVER_PROTOCOL\"].' 500 Internal Server Error',true,500);echo $e->getMessage();die();}};echo'ok';"
            )
        phpfile.close()
        self.uploadFile(phpfilename, self.config['remote']['public-web-path'])
        return phpfilename

    def extractRemote(self, apitoken = False):
        if(not apitoken):
            apitoken = self.apiToken
        phpfilename = self.phpTempFile
        print(message().iDebug() + f"token:{apitoken}")
        headers = {'X-API-TOKEN': apitoken}
        data = {'title': 'value1', 'name': 'value2'}
        callUrl = os.path.join(
            self.config['remote']['public-web-url'], phpfilename)
        print(f"Trying to extract remote archive. Calling: {callUrl} ... ", end='')
        response = requests.post(
            callUrl, headers=headers, data=json.dumps(data))
        if((response.status_code == 200) and (str(response.content) == "b'ok'")):
            print(bcolors.OKGREEN + "OK" + bcolors().ENDC)
            return True
        else:
            print(bcolors().FAIL + "ERROR" + bcolors().ENDC)
            print("Sorry, problem extractiong archive. Check server response below for details")
            print(str(response.content))
            sys.exit()
        return True

    def removeRemote(self, file, folder = False):
        print(f"Removing remote {file}")
        if(folder):
            self.ftp.cwd(folder)
        result = self.ftp.delete(file)        
        return result

    #
    # removes local temp files
    #
    def cleanUpLocal(self):
        if(os.path.exists(self.archiveTempFile)):
            os.remove(self.archiveTempFile)
        if(os.path.exists(self.phpTempFile)):
            os.remove(self.phpTempFile)
        if(os.path.exists(self.tempRemoteComposerLockFile)):
            os.remove(self.tempRemoteComposerLockFile)
        return True

    #
    # removes remote remp files
    #
    def cleanUpRemote(self):
        phpFileFtp = "/" + self.config['remote']['public-web-path'].strip("/") + "/" + self.phpTempFile.strip("/")
        self.ftp.delete(phpFileFtp)
        tarfilename = "/" + self.config['remote']['remote-root'].strip("/") + "/" + self.archiveTempFile.strip("/")
        self.ftp.delete(tarfilename)
        return True

    ###
    #
    # UPLOAD packages
    #
    def uploadComposerPackages(self):
        packages = self.packagesToUpload + self.packagesToUpdate
        allOk = True
        # create list of files to archive
        filelist = [
            'composer.json',
            'composer.lock',
            'vendor/composer',
            'vendor/bin'
        ]
        for package in packages:
            filelist.append(os.path.join('vendor', package['name']))

        archiveFile = self.makeArchive(filelist)
        destFolder = self.config['remote']['remote-root']
        self.uploadFile(archiveFile, destFolder)            
        return True
       
    ###
    #
    # UPDATE composer files
    #
    def compareComposerFiles(self):
        print("Comparing composer.lock files...")
        localComposer = self.getLocalPackages()
        remoteComposer = self.getRemotePackages()
        localPackages = {}
        remotePackages = {}

        packagesToUpload = []
        packagesToUpdate = []
        packagesToRemove = []

        for package in localComposer['packages']:
            localPackages[package['name']] = package
        for package in localComposer['packages-dev']:
            localPackages[package['name']] = package

        for package in remoteComposer['packages']:
            remotePackages[package['name']] = package
        for package in remoteComposer['packages-dev']:
            remotePackages[package['name']] = package

        for packageName in localPackages:
            localPackage = localPackages[packageName]
            if packageName in remotePackages:
                remotePackage = remotePackages[packageName]
                if (localPackage['version'] != remotePackage['version']):
                    packagesToUpdate.append(localPackage)
            else:
                packagesToUpload.append(localPackage)
        for packageName in remotePackages:
            if not (packageName in localPackages):
                remotePackage = remotePackages[packageName]
                packagesToRemove.append(remotePackage)

        print("Packages to update:")
        if(len(packagesToUpdate) == 0):
            print("(none)")
        else: 
            for package in packagesToUpdate:
                print("\t{}\t\tlocal: {}\tremote: {}".format(package['name'], localPackages[package['name']]['version'], remotePackages[package['name']]['version']))   
            
        print("\nPackages to upload:")
        if(len(packagesToUpdate) == 0):
            print("(none)")
        else:
            for package in packagesToUpload:
                print("\t{}\t\tlocal: {}".format(package['name'], localPackages[package['name']]['version']))        

        print("\nPackages to remove:")
        if(len(packagesToUpdate) == 0):
            print("(none)")
        else:        
            for package in packagesToRemove:
                print("\t{}\t\t\tremote: {}".format(package['name'], remotePackages[package['name']]['version']))
        
        print("\n")
        self.packagesToRemove = packagesToRemove
        self.packagesToUpdate = packagesToUpdate        
        self.packagesToUpload = packagesToUpload
        if((len(packagesToRemove) + len(packagesToUpdate)+len(packagesToUpload)) >0):
            return True
        else:
            return False

    def runSync(self):
        self.loadConfig()
        if ('remote-root' not in dict(self.config['remote']).keys()):
            print("Error: 'remote-root' is missing in .git/config!\n")
            exit()
        isSyncNeeded = self.compareComposerFiles()
        if(isSyncNeeded):
            self.removeRemotePackages()
            self.removeRemotePackages()
            self.uploadComposerPackages()
            self.makePhpExtractScript()
            self.extractRemote()
            self.cleanUpLocal()
            self.cleanUpRemote()       
        else:
            print("Nothing to do. Everything seems to up to date.\n")
        print(message().iOk() + "Done.\n")        
        return True
    #
    #
    #
    def fullUpload(self):
        self.loadConfig()
        self.getRemoteConnection()        
        filelist = [
            'composer.json',
            'composer.lock',
            'vendor'            
        ]
        self.makeArchive(filelist)
        self.uploadFile(self.archiveTempFile, self.config['remote']['remote-root'])        
        self.makePhpExtractScript()        
        self.extractRemote()
        self.cleanUpLocal()
        self.cleanUpRemote()         
        return True
    #
    #
    #
    def showConfig(self):
        print("Current config is:")
        for section in self.config.sections():
            print("[{}]".format(section))
            for key in self.config[section]:
                print("   {} = {}".format(key, self.config[section][key]))
        print("\n")
        return True
    #
    #
    #
    def showHelp(self):
        helpTxt = "\nUsage:\n\
\t{} command [options]\n\n\
Available commands:\n\
\tinit - upload full vendor dir\n\
\tsync - run composer/vendor syncronisation\n\
\tshow-config - show configuration\n\
\tmake-config - create a .tunec.conf file\n\
\thelp - well, obviously just a help\n\n\
Example configuration file:\n\
[remote]\n\
\turl = ftp://ftp.myproject.com/\n\
\tuser = user@myproject.com\n\
\tpassword = password123\n\
\tremote-root = /www/html/public/\n\
\tpublic-web-url = http://www.myproject.com/\n\n\
For more detailed help and some more explanations please take a look at README.md\n"
        print(helpTxt.format(sys.argv[0]))
        return True

    def test(self):
        self.loadConfig()
        self.phpTempFile = 'tunec_8vncl48t.php'
        self.extractRemote('82cnrin8')

    def run(self):
        if (sys.argv.__len__() == 1):
            command = "help"
        else:
            command = sys.argv[1]
        match command:
            case "sync":
                self.runSync()
            case "show-config":
                self.showConfig()
            case "make-config":
                self.makeConfig()
            case "init":
                self.fullUpload()
            case "help":
                self.showHelp()
            case "test":
                self.test()
            case _:
                self.showHelp()
        return True

#
# start main procedure
#
sync = ComposerSync()
sync.run()
