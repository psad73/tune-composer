#!/usr/bin/python
import os, sys, re, json, tarfile, tempfile, requests
import urllib.parse
from urllib.parse import urlparse
from configparser import ConfigParser
from ftplib import FTP


class ComposerSync:
    configFile = '.tunec.cfg'
    config = []
    ftp = ''
    tempRemoteComposerLockFile = 'composer.remote.lock'
    def __init__(self):
        self.readConfig()        
        #self.getRemoteConnection()
        return 
    
    ################
    #
    # readConfig
    #
    #
    def readConfig(self):
        configObj = ConfigParser()
        if(os.path.isfile(self.configFile)):
            configObj.read(self.configFile)                    
            self.config = configObj                        
        else:
            gitConfigObj = ConfigParser()
            gitConfigObj.read(".git/config")
            if(not('git-ftp' in gitConfigObj.sections())):
                print("You don't have a [git-ftp] in your .git/config nor a .tunec.conf file?! Not good...")
                exit()
            self.config = ConfigParser()
            self.config.add_section('remote')
            for key in  dict(gitConfigObj['git-ftp']).keys():
                if(key == 'url'):
                    parsed_uri = urlparse(gitConfigObj['git-ftp'][key])
                    host = parsed_uri.netloc
                    self.config.set('remote', 'host', host) 
                self.config.set('remote', key, gitConfigObj['git-ftp'][key])            
            if('httpcallurl' in gitConfigObj['git-ftp']):
                self.config.set('remote', 'httpcallurl', gitConfigObj['git-ftp']['httpcallurl'])
            else:                                
                httpcallurl = 'http://' + urllib.parse.urlparse(self.config['remote']['url']).netloc  + '/'
                self.config.set('remote', 'httpcallurl', httpcallurl)    

    ###
    #
    # makeConfig
    #
    #
    def makeConfig(self):
        overWrite = True
        if(os.path.isfile(self.configFile)):
            user_input = input(f"{self.configFile} exists. Overwrite? (yes/no): ")
            if user_input.lower() == 'yes':
                overWrite = True
            else:
                overWrite = False
        if(overWrite):
            with open(self.configFile, 'w') as configfile:
                self.config.write(configfile)
        return True

    def getLocalPackages(self):
        f = open('composer.lock')
        localComposer = json.load(f)
        return localComposer
            
    def getRemotePackages(self):
        temporaryRemoteComposerFile = self.tempRemoteComposerLockFile
        ftp = self.getRemoteConnection()        
        #ftp.dir()
        #ftp.retrlines('composer.lock')
        with open(temporaryRemoteComposerFile ,'wb') as fp:
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

    def getRemoteDirs(self, path):
        remoteFtpEntries = []
        self.ftp.cwd(path)
        self.ftp.retrlines('LIST',remoteFtpEntries.append)
        dirlist = []
        for line in remoteFtpEntries:
            regexp = "^(?P<perm>[Sldrwx\-]{10})(?:\s+)(?P<cos>\d+)(?:\s+)(?P<user>\w+)(?:\s+)(?P<group>\w+)(?:\s+)(?P<size>\d+)(?:\s+)(?P<month>\w+)(?:\s+)(?P<day>\d+)(?:\s+)(?P<timeyear>[0-9\:]+)(?:\s+)(?P<filename>.*)"
            entry = re.match(regexp, line)
            if((re.match("^d", entry.group('perm')))and( not re.match("^\.", entry.group('filename')))):
                dirlist.append(entry.group('filename'))
        return dirlist

    def uploadThis(self, ftp, path):        
        print("Uploading folder: ", path)
        files = os.listdir(path)
        remoteFtpEntries = []
        ftp.retrlines('LIST',remoteFtpEntries.append)
        filelist = []
        dirlist = []
        for line in remoteFtpEntries:
            regexp = "^(?P<perm>[Sldrwx\-]{10})(?:\s+)(?P<cos>\d+)(?:\s+)(?P<user>\w+)(?:\s+)(?P<group>\w+)(?:\s+)(?P<size>\d+)(?:\s+)(?P<month>\w+)(?:\s+)(?P<day>\d+)(?:\s+)(?P<timeyear>[0-9\:]+)(?:\s+)(?P<filename>.*)"
            entry = re.match(regexp, line)
            #print(entry.group('perm'))
            if((re.match("^d", entry.group('perm')))and( not re.match("^\.", entry.group('filename')))):
                dirlist.append(entry.group('filename'))
            if(re.match("^\-", entry.group('perm'))):
                filelist.append(entry.group('filename'))

        #print(dirlist)
        #print(filelist)

            #print(entry.group('user'))
            
        for f in files:
            print(f)
            absFile = os.path.abspath(os.path.join(os.curdir, path, f))
        #     print("file", absFile, os.path.isfile(absFile))            
            if os.path.isfile(os.path.join(os.curdir, path, f)):                
                fh = open(absFile, 'rb')
                command = 'STOR %s' % os.path.join(path, f)
                self.prepareRemoteDir(ftp, os.path.dirname(os.path.join(path, f)))
                print(command)
                ftp.storbinary(command, fh)
                fh.close()
                #     elif os.path.isdir(path + r'\{}'.format(f)):
                #         ftp.mkd(f)
                #         ftp.cwd(f)                
                #         self.uploadThis(path + r'\{}'.format(f))
                # ftp.cwd('..')
                # os.chdir('..')
    
    def prepareRemoteDir(self, ftp, file):
        path = re.split("/", file)        
        remoteDirs = self.getRemoteDirs('')
        print(remoteDirs)
        

    def getRemoteConnection(self):
        ftp = FTP(self.config['remote']['host'])        
        ftp.login(user=self.config['remote']['user'], passwd=self.config['remote']['password'])
        ftp.cwd(self.config['remote']['remote-root'])
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
            print("\tProblem removing remote {}".format(package['name']))
        else:
            print(" Package {} removed".format(package['name']))

    def removeRemotePackages(self, packages):        
        for package in packages:
            self.removeRemotePackage(package)
    ###
    #
    # UPDATE packages
    #
    def updateRemotePackage(self, package):
        ftp = self.getRemoteConnection()

    def updateRemotePackages(self, packages):        
        for package in packages:
            print("updating: {}".format(package['name']))  

    ###
    #
    # UPLOAD packages
    #
    def uploadRemotePackageTest(self, package):        
        self.removeRemotePackage(package)
        print("uploading: {}".format(package['name']))    
        ftp = self.getRemoteConnection()        
        self.uploadThis(ftp, "vendor/" + package['name'])

    def uploadRemotePackage(self, package):
        directory = pathlib.Path("vendor/" + package['name'])
        with ZipFile("vendor.zip", "a", ZIP_DEFLATED, compresslevel=9) as archive:
            for file_path in directory.rglob("*"):
                archive.write(file_path, arcname=file_path.relative_to(directory))

    def uploadComposerPackages(self, packages):
        allOk = True
        tarfilename = next(tempfile._get_candidate_names()) + ".tar.gz"
        apitoken = next(tempfile._get_candidate_names())
                
        # create list of files to archive
        filelist = [
            'composer.json',
            'composer.lock',
            'vendor/composer',
            'vendor/bin'
        ]    
        for package in packages:            
            filelist.append(os.path.join('vendor', package['name']))

        # create tar archive    
        tar = tarfile.open(tarfilename, mode='w:gz')
        for entry in filelist:
            tar.add(entry)
        tar.close()

        # upload tar archive
        fh = open(tarfilename, 'rb')
        self.ftp.storbinary(f"STOR {tarfilename}", fh)
        fh.close()

        # create php extract file        
        phpfilename = next(tempfile._get_candidate_names()) + ".php"
        phpfile = open(phpfilename, 'w')  
        phpFileFtp =  f"{self.config['remote']['publicweb-root']}{phpfilename}"
        phpfile.write(f"<?php if(filter_input(INPUT_SERVER, 'HTTP_X_API_TOKEN') != '{apitoken}') die(); $phar = new PharData('{tarfilename}'); $phar->extractTo('.', null, true); echo 'ok';")
        phpfile.close()

        #upload php file        
        fh = open(phpfilename, 'rb')
        up = self.ftp.storbinary(f"STOR {phpFileFtp}", fh)
        print(up)
        fh.close()

        # curl call to extract
        
        headers = {'X-API-TOKEN': apitoken}
        data = {'title' : 'value1', 'name':'value2'}
        callUrl = os.path.join(self.config['remote']['httpcallurl'] , phpfilename)        
        print(f"Calling: {callUrl}")
        response = requests.post(callUrl, headers=headers, data=json.dumps(data))
        proceed_with_remove = True
        if((response.status_code != 200) and (response.text != 'ok')):
            allOk = False
            print("Something went wrong while extracting composer archive!")
            print(response)
            user_input = input('Remove temp files? (yes/no): ')
            if user_input.lower() == 'yes':
                proceed_with_remove = True
            else:
                proceed_with_remove = False
        #remove local temps        
        if(proceed_with_remove):
            os.remove(phpfilename)
            os.remove(tarfilename)
            os.remove(self.tempRemoteComposerLockFile)

        #remove remote temps
            self.ftp.delete(phpFileFtp)
            self.ftp.delete(tarfilename)
        return allOk
    ###
    #
    # UPDATE composer files
    #
    def updateRemoteComposer(self):
        ftp = self.getRemoteConnection()


    def compareComposerFiles(self):
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
                if(localPackage['version'] != remotePackage['version']):                    
                    packagesToUpdate.append(localPackage)
            else:
                packagesToUpload.append(localPackage)
        for packageName in remotePackages:
            if not(packageName in localPackages):
                remotePackage = remotePackages[packageName]
                packagesToRemove.append(remotePackage)
            
        print("Packages to update:")        
        for package in packagesToUpdate:
            print("\t{}\t\tlocal: {}\tremote: {}".format(package['name'], localPackages[package['name']]['version'], remotePackages[package['name']]['version']))            
        print("\nPackages to upload:")
        for package in packagesToUpload:
            print("\t{}\t\tlocal: {}".format(package['name'], localPackages[package['name']]['version']))
        print("\nPackages to remove:")        
        for package in packagesToRemove:
            print("\t{}\t\t\tremote: {}".format(package['name'], remotePackages[package['name']]['version']))

        self.removeRemotePackages(packagesToRemove)        
        self.removeRemotePackages(packagesToUpdate)
        self.uploadComposerPackages(packagesToUpload + packagesToUpdate)

    def runSync(self):
        if('remote-root' not in dict(self.config['remote']).keys()):
            print("Error: 'remote-root' is missing in .git/config!\n")
            exit()
        sync.compareComposerFiles()
        return True

    def showConfig(self):
        print("Current config is:")
        for section in self.config.sections():
            print("[{}]".format(section))
            for key in self.config[section]:                
                print("   {} = {}".format(key, self.config[section][key]))
        print("\n")        
        return True
    
    def showHelp(self):        
        helpTxt = "\nUsage:\n\
\t{} command [options]\n\n\
Available commands:\n\
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
\thttpcallurl = http://www.myproject.com/\n\n\
For more detailed help and some more explanations please take a look at README.md\n"        
        print(helpTxt.format(sys.argv[0]))        
        return True
    
    def run(self):
        if(sys.argv.__len__() == 1):
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
            case "help":        
                self.showHelp()
            case _:
                self.showHelp()
        return True

sync = ComposerSync()
sync.run()
