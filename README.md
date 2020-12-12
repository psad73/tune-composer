# tune-composer (tune c, tunec)
Script for updating composer/vendor without shell access at production server.

Ugly written, but working (soon).

## Why?

Because I'm tired of uploading +800MB of files everytime one library is updated. Even with zip it takes too much time.

## Why HG/Merurial?

Because it does not collide with the git system. 

## How to?

1. First configure the local and remote params in tunec.yaml
2. Make a first, init for the local vendor directory
    

## Things still have to be done

- Add simple FTP protocol 
- The script is not very foolproof. some additional checkes (file/folder location, permission, etc) should be added.
- Empty, unnecessary folder are not deleted. No idea how to solve this problem yet. But it seems a less problem while in develop stage. I assume, updates in production mode are not performed too often. Before entering the prod mode, it is enough to make full update (clean init).
- Directory permissions are not kept. well...
- Code cleanup. As always.

## Versions

0.01 - initial, testing

0.02 - first working version
