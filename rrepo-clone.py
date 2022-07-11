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
import time
import pathlib
import xml.etree.ElementTree as ET
import gzip
import shutil
import sys
######################

# persistent TCP connection
httpSes = requests.Session()

# Retries on errors
connRetries = 3
connRetryDelay = 20

class Ctx:
    """Application context"""
    ishttp: bool = None
    repofiles = set()
    repodirs = set()
    nnewfiles: int = 0
    nfailedfiles: int = 0
    ndownsize: float = 0.0

ctx = Ctx()


class Logger():
    """ Logging both stdout & file """
    def __init__(self, fn:str = ''):
        self.con = sys.stdout
        self.file = open(fn, 'at') if fn else None

    def write(self, message):
        self.con.write(message)
        if self.file:
            self.file.write(message)

    def flush(self):
        self.con.flush()
        if self.file:
            self.file.flush()
#


def parse_cmdline():
    """Parses command line arguments and updates `ctx`"""

    parser = argparse.ArgumentParser()
    parser.add_argument('baseurl', metavar="http(s)://source/url/",
                        help="Source url ('http:', 'https' or 'file:') of the RPM repo root dir "
                             "having /repodata/repomd.xml.")
    parser.add_argument('basedir', metavar="/destination/dir/",
                        help="Destination path where all files and metadata "
                        "will be downloaded, if does not exist it will be "
                        "created.")
    parser.add_argument('--arch', metavar="x86_64", action='append',
                        help='architecture(s) to download packages for, may be specified multiple times')
    parser.add_argument('--noclean', action='store_true', default=False,
                        help="don't delete old packages not in the repo")
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
                        help="be more verbose, report existing packages")
    parser.add_argument('--log', metavar="FILE",
                        help="additionally append log messages to FILE")
    parser.parse_args(namespace=ctx)

    colon = ctx.baseurl.find(':')
    if colon >= 0:  # protocol is specified
        if ctx.baseurl.startswith(('http:','https:')):
            ctx.ishttp = True
        elif ctx.baseurl.startswith('file:'):  # local filesystem
            ctx.ishttp = False
            ctx.baseurl = ctx.baseurl[len('file:/'):]
        else:
            printf(f"Unsupported URL protocol. Only http:, https: or file: are required")
    else:  # protocol is not specified -> local filesystem
        ctx.ishttp = False
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

    fmtsize = f" ({size/1024./1024.:.2f} MiB)" if size > 0 else ""

    path = pathlib.Path(ctx.basedir, fn)
    if path.exists() and path.stat().st_size == size:
        if ctx.verbose:
            print(f"{fn} exists")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)

        if ctx.ishttp:
            # Downloading from the Internet
            #
            url = requests.compat.urljoin(ctx.baseurl, fn)

            for n in range(connRetries):
                if n > 0:
                    print(f"... Retry in {connRetryDelay} sec")
                    time.sleep(connRetryDelay)
                try:
                    print(f"{fn}{fmtsize} ", end='', flush=True)
                    downsize = 0
                    with httpSes.get(url, stream=True) as r:
                        r.raise_for_status()
                        with open(path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=1024*1024):
                                downsize += len(chunk)
                                f.write(chunk)
                    print(f"downloaded")
                    ctx.nnewfiles += 1
                    ctx.ndownsize += downsize
                    break

                except requests.exceptions.HTTPError as exc:
                    code = exc.response.status_code
                    print("download FAILED")
                    print(exc)
                    if code in [404, 429, 500, 502, 503, 504]:
                        continue  # retry
                    raise exc

                except requests.exceptions.ConnectionError as exc:
                    print("download FAILED")
                    print(exc)
                    continue  # retry
            else:  # retries finished
                print("ERROR: package skipped")
                ctx.nfailedfiles += 1
        else:
            # Copying from the local filesystem
            #
            url = pathlib.Path(ctx.baseurl, fn)
            print(f"{fn}{fmtsize} ", end='')
            try:
                shutil.copyfile(url, path)
                print(f"copied")
                ctx.nnewfiles += 1
                ctx.ndownsize += url.stat().st_size
            except OSError as exc:
                print("FAILED to copy")
                print(exc)
                ctx.nfailedfiles += 1

    ctx.repofiles.add(fn)
    ctx.repodirs.add(str(pathlib.Path(fn).parent))
    return str(path)
#


def main():
    parse_cmdline()
    if ctx.ishttp is None:  return

    # Logging
    sys.stdout = Logger(ctx.log)

    print("\n"
          "###\n"
         f"### Cloning {ctx.baseurl}, archs {ctx.arch}\n"
         f"### to {ctx.basedir}\n"
          "###")

    # Load metadata files
    metafile: str = ''
    repomd = ET.parse(download('repodata/repomd.xml'))
    ns = '{http://linux.duke.edu/metadata/repo}'  # xml namespace
    for e in repomd.findall(f'{ns}data'):
        fn = e.find(f'{ns}location').get('href')
        sz = int(e.find(f'{ns}size').text)
        path = download(fn, sz)
        if fn.endswith('primary.xml.gz'):
            metafile = path
    download('repodata/repomd.xml.asc')
    download('repodata/repomd.xml.key')

    # Parse metafile & download RPMs
    print("")
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

    print("")
    print(f"--- {ctx.nnewfiles} new files ({ctx.ndownsize/1024./1024.:.2f} MiB) have been obtained")
    if ctx.nfailedfiles > 0:
        print(f"--- WARNING: {ctx.nfailedfiles} files have been FAILED to obtain")

    # Clear old files not in the repo
    ndelfiles = 0
    if not ctx.noclean:
        print("\n"
              "---\n"
             f"--- Cleaning old files in {ctx.basedir}{ctx.repodirs}\n"
              "---")
        for d in ctx.repodirs:
            dd = pathlib.Path(ctx.basedir, d)
            if not dd.is_dir():
                continue;
            for f in dd.iterdir():
                if not f.is_file():
                    continue
                fn = str(f.relative_to(ctx.basedir))
                if not fn in ctx.repofiles:
                    f.unlink()
                    print(f'{fn} deleted')
                    ndelfiles += 1

    print(f"\n--- {ndelfiles} old files have been deleted")
#


if __name__ == "__main__":
    main()
