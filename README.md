# RPM Repositories Cloning tool

Clones repositories in RPM-MD format with optionally selecting just needed architectures. Written in Python-3.6+. Tested on OpenSUSE-Leap repositories.
Inspired by [rrclone](https://github.com/eleksir/rrclone) perl tool.

## Getting Started
```
rrepo-clone.py  --arch x84_64 --arch noarch  http://source/repo/   path/to/destination/folder/
```

### Prerequisites
Python3 environment with at least 3.6 version of python running under any OS (Windows, Linux, etc). Python modules required: `Requests` and several standard ones.

### Using rrclone
You need a correct path to repository. For example, take it from a .repo-file (located in '/etc/yum.repos.d' (RedHat) or '/etc/zypp/repos.d' (SUSE) dirs) as a string after "baseurl=". To check that url is correct you can try to download part of repository xml metadata. Put your string into browser address bar and append "/repodata/repomd.xml" (no quotes) and if you see xml text then the url is correct.

By default, the `rrepo-clone` downloads packages for all architectures available. If only several are required (e.g. 'x86_64' and 'noarch'), provide one or many `--arch <name>` options in the command line.
