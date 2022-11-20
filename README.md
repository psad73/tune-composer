*** forgett about the tunec php version here. it's working, but... don't***

# tune.py 
Script for updating composer/vendor without shell access at production server.

Requirements:
- Linux (tested on Ubuntu 22.04)
- python3.10 (probably working with 2.7, but not tested)
- some python libs, like: os, sys, re, json, tarfile, tempfile, requests, urllib.parse, configparser, ftplib

## Why?

Because I'm tired of uploading +800MB of files everytime one library is updated. It takes too much time.

## How to?

Basic usage: 
    tunec.py command [options]

Available commands:
    sync - run composer/vendor syncronisation
    config - show configuration
    help - well, obviously just a little help

Example configuration file (.tune.conf):
```
[remote]
    url = ftp://ftp.myproject.com/
    user = user@myproject.com
    password = password123
    remote-root = /www/html/public/
    httpcallurl = http://www.myproject.com/
```

Now, the script will download the remote "composer.lock" file and compare with the local file. Libreries present in the remove `/vendor` directory, but missing localy will be removed at remote host. They are probably no needed, right? Those with different version number are removed as well. However, these are copied from local /vendor folder to the remote. Finally, local `vendor/composer`, `vendor/bin`, `composer.json` and `composer.lock` are uploaded to remote host. No need to upload whole, 1GB+ big `vendor` folder! Hurray!


**Fun fact:** You can place this configuration in `.git/config` replacing the [remote] section name with [git-ftp]. Yes, as some may have noticed, the script use the same configuratio as git-ftp extension. This allows you to use the same configuration for both utils. Saves a lof time to configure both ;) The only, additional config option is "httcallurl" which is not recognized by git-ftp, but should not break it's functions.
Of course, a `.tunec.conf` in the current directory will override the git-ftp config. Just in case, you need a differnt settings for some, mysterious reason.