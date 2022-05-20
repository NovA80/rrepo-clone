#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RPM Repositories Cloning tool

Clones repositories in RPM-MD format with specifing needed archs.

Created on May 2022

@author: Andrey Novikov aka NovA
"""

import argparse
import requests
import pathlib
import xml.etree.ElementTree as ET
import gzip

# persistent TCP connection
httpSes = requests.Session()

# program context (base url, destination dir, ...)
class Ctx:
    repofiles = set()
    nnewfiles = 0

ctx = Ctx()

def parse_cmdline():
    """Parse command line arguments and update `ctx`"""
    
    parser = argparse.ArgumentParser()
    parser.add_argument('baseurl', metavar="http://source/url/",
                        help="Source http(s) url of the RPM repo root dir"
                             "having /repodata/repomd.xml.")
    parser.add_argument('basedir', metavar="/destination/dir/",
                        help="Destination path where all files and metadata "
                        "will be downloaded, if does not exist it will be "
                        "created.")
    parser.add_argument('--arch', metavar="x86_64", action='append',
                        help='architecture(s) to download packages for, may be specified multiple times')
    parser.add_argument('--noclean', action='store_true', default=False,
                        help="don't delete old packages not in the repo")
    parser.parse_args(namespace=ctx)
#


def download(fn: str, size: int = -1):
    """
    Downloads file from baseurl/fn and saves to basedir/fn

    Args:
        fn: filename
        size: required file size

    Returns:
        path of the loaded file
    """
    path = pathlib.Path(ctx.basedir, fn)
    if path.exists() and path.stat().st_size == size:
        print(f'{fn} exists')
    else:
        url = requests.compat.urljoin(ctx.baseurl, fn)
        path.parent.mkdir(parents=True, exist_ok=True)

        with httpSes.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    f.write(chunk)
        print(f'{fn} ({size/1024./1024.:.2f} MiB) downloaded')
        ctx.nnewfiles += 1

    ctx.repofiles.add(fn)
    return str(path)
#


if __name__ == "__main__":
    parse_cmdline()

    print("---\n"
         f"--- Cloning {ctx.baseurl} archs {ctx.arch}\n"
         f"--- to {ctx.basedir}\n"
          "---")

    # Load metadata files
    metafile: str = ''
    repomd = ET.parse(download('repodata/repomd.xml'))
    ns = '{http://linux.duke.edu/metadata/repo}'  # xml namespace
    for e in repomd.findall(f'{ns}data/{ns}location'):
        fn = e.get('href')
        path = download(fn)
        if fn.endswith('primary.xml.gz'):
            metafile = path
    download('repodata/repomd.xml.asc')
    download('repodata/repomd.xml.key')


    # Parse metafile & download RPMs
    print("\n")
    ns = '{http://linux.duke.edu/metadata/common}'  # xml namespace
    with gzip.open(metafile, 'rb') as f:
        for _, e in ET.iterparse(f):
            if e.tag == f'{ns}package':
                arch = e.find(f'{ns}arch').text
                if not ctx.arch or arch in ctx.arch:
                    fn = e.find(f'{ns}location').get('href')
                    sz = int(e.find(f'{ns}size').get('package'))
                    download(fn, sz)
                e.clear()  # !!! a must, memory hog otherwise

    # Clear old files not in the repo
    ndelfiles = 0
    if not ctx.noclean:
        print("\n"
              "---\n"
             f"--- Cleaning old files in {ctx.basedir}\n"
              "---")
        for p in pathlib.Path(ctx.basedir).rglob('*'):  # all local files
            if not p.is_file():
                continue

            fn = str(p.relative_to(ctx.basedir))
            if not fn in ctx.repofiles:
                p.unlink()
                print(f'{fn} deleted')
                ndelfiles += 1
    
    print("\n"
          "---\n"
         f"--- Repository {ctx.baseurl} clone finished\n"
          "---")
    print(f"{ctx.nnewfiles} new files have been downloaded")
    print(f"{ndelfiles} old files have been deleted")
#
