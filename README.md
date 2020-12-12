# tune-composer (tune c, tunec)
Script for updating composer/vendor without shell access at production server.

Ugly written, but working.

Requirements:
- Linux (tested on Ubuntu 20.04)
- php 7.3+ (not tested in other versions)
- hg (Mercurial SCM https://www.mercurial-scm.org) installed in the local system

## Why?

Because I'm tired of uploading +800MB of files everytime one library is updated. Even with zip it takes too much time.

## Why HG/MercurialSCM?

Seems to be pretty to use. And it does not collide with the git system used in lot of composer packages.

## How to?

1. First configure the local and remote params in tunec.yaml
2. Make a first, init for the local vendor directory. The local vendor direcotry will be put under version control

    ``# php index.php projectname initlocal``

3. Make remote init - the first update will copy all files to the remote location

	``# php index.php projectname initremote``

4. Now, if everything works fine, you may check the sync status

	``# php index.php projectname status``

5. Or make a regular update after adding/removing a composer library

	``# php index.php projectname push``

## Things still have to be done

- The script is not very foolproof. some additional checkes (file/folder location, permission, etc) should be added.
- Empty, unnecessary folder are not deleted. No idea how to solve this problem yet. But it seems a less problem while in develop stage. I assume, updates in production mode are not performed too often. Before entering the prod mode, it is enough to make full update (clean init).
- Directory permissions are not kept. well...
- Code cleanup. As always.

## Versions

0.01 - initial, testing

0.02 - first working version
