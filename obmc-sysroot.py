#!/usr/bin/python3
# coding: utf-8

import argparse
import glob
import os.path
import shutil
import sys


def parse_args():
    parser = argparse.ArgumentParser('obmc-sysroot')
    parser.add_argument(
        '-b', '--build',
        dest='build',
        required=True,
        help='openbmc build dir'
    )
    parser.add_argument(
        '-r', '--root',
        dest='root',
        required=True,
        help='root dir to create'
    )
    parser.add_argument(
        '-v', '--verbose',
        dest='verbose',
        action='store_true',
        default=False,
        help='more verbose'
    )
    return parser.parse_args()


def setup_root(build, root, verbose):
    if not os.path.exists(build):
        print("build dir does not exist", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(root) and os.listdir(root):
        print("root dir already exists and is not empty", file=sys.stderr)
        sys.exit(1)

    sstate = os.path.join(build, 'tmp/sstate-control')
    if not os.path.exists(sstate):
        print("tmp/sstate-control dir does not exist", file=sys.stderr)
        sys.exit(1)

    os.makedirs(root, exist_ok=True)

    manifests = os.path.join(sstate, 'manifest-*.populate_sysroot')
    for i in glob.glob(manifests):
        n = os.path.basename(i)
        n = n.removeprefix('manifest-')
        n = n.removesuffix('.populate_sysroot')

        # conflicts with libgcc
        if n.endswith('libgcc-initial'):
            continue

        native = False
        if n.endswith("-native") or "-cross-" in n or "-crosssdk" in n:
            native = True

        sysroot = os.path.join(root, 'sysroot')
        if native:
            sysroot = os.path.join(root, 'sysroot-native')

        with open(i, 'r') as f:
            for s in f:
                s = s.strip()
                if s.endswith('/fixmepath'):
                    continue
                if s.endswith('/fixmepath.cmd'):
                    continue

                d = s.replace(build, '')
                d = '/'.join(d.split('/')[5:])
                d = os.path.join(sysroot, d)
                if s.endswith('/'):
                    if verbose:
                        print(f'mkdirs {d}')
                    os.makedirs(d, exist_ok=True)
                    continue
                ddir = os.path.dirname(d)
                if not os.path.exists(ddir):
                    if verbose:
                        print(f'mkdirs {ddir}')
                    os.makedirs(ddir)
                if os.path.isdir(s):
                    if verbose:
                        print(f'copytree {s} -> {d}')
                    shutil.copytree(s, d)
                    continue
                if os.path.islink(s):
                    to = os.readlink(s)
                    if os.path.lexists(d):
                        if os.readlink(d) == to:
                            continue
                if verbose:
                    print(f'copy {s} -> {d}')
                # use copy to preserve file permission bits
                shutil.copy(s, d, follow_symlinks=False)


def print_usage(root):
    export = f'''export PATH=\\
{root}/sysroot-native/usr/bin/arm-openbmc-linux-gnueabi:\\
{root}/sysroot/usr/bin/crossscripts:\\
{root}/sysroot-native/usr/sbin:\\
{root}/sysroot-native/usr/bin:\\
{root}/sysroot-native/sbin:\\
{root}/sysroot-native/bin\\
$PATH
'''

    sysroot = f'''GCC --sysroot={root}/sysroot, e.g.,
arm-openbmc-linux-gnueabi-gcc --sysroot=/home/runsisi/working/test/bmcroot/sysroot -o x x.c
arm-openbmc-linux-gnueabi-gdb ./x
'''

    print('\n*** setup bmc sysroot succeeded! ***\n')
    print(f'{export}\n{sysroot}')


if __name__ == '__main__':
    args = parse_args()
    build = os.path.abspath(os.path.expanduser(args.build))
    root = os.path.abspath(os.path.expanduser(args.root))
    setup_root(build, root, args.verbose)
    print_usage(root)
