# RPM Repositories Cloning tool

Clones repositories in RPM-MD format with optionally selecting just needed architectures. Written in Python-3.6+. Tested on OpenSUSE-Leap repositories.
Inspired by [rrclone](https://github.com/eleksir/rrclone) perl tool.

## Getting Started
```
rrepo-clone.py  --arch x84_64 --arch noarch  http://source/repo/   path/to/destination/folder/
```

### Prerequisites
Python-3 environment with at least 3.6 version running under any OS (Windows, Linux, etc). Python modules required: `Requests` and several standard ones.

### Using rrclone
There are no additional effort required for one-shot sync.

You need correct path to repository. A string after "baseurl=" in repo-file (e.g. one that located in /etc/yum.repos.d (RedHat) or /etc/zypp/repos.d (SUSE)). To check that url is correct you can try to download part of repository xml metadata. Put your string into browser address bar and add "/repodata/repomd.xml" (no quotes) and if you see xml text then the url is correct.

By default, the `rrepo-clone` downloads packages for all architectures available. If only sevaral are required (e.g. x86_64 and noarch), provide one or many `--arch <aaa>` options in the command line.
