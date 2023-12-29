#!/usr/bin/python3
# coding: utf-8

import argparse
import os
import sys
import logging


class Tee:
    def __init__(self, *files):
        self._files = files

    def __getattr__(self, attr, *args):
        return self._wrap(attr, *args)

    def _wrap(self, attr, *args):
        def g(*a, **kw):
            for f in self._files:
                r = getattr(f, attr, *args)(*a, **kw)
            return r
        return g


def parse_args():
    parser = argparse.ArgumentParser('obmc-server')
    parser.add_argument(
        '-b', '--build',
        dest='build',
        required=True,
        help='openbmc build dir'
    )
    return parser.parse_args()


def run(build):
    libpath = os.path.abspath(os.path.join(build, '../../bitbake/lib'))
    sys.path.insert(0, libpath)

    import bb.event
    import bb.utils
    import bb.server.process

    bb.utils.check_system_locale()

    logfile = os.path.join(build, 'bitbake-cookerdaemon.log')
    lockname = os.path.join(build, 'bitbake.lock')
    sockname = os.path.join(build, 'bitbake.sock')

    lock = bb.utils.lockfile(lockname, False, False)
    if not lock:
        print('bitbake server is already running, please run `bitbake -m` to kill')
        sys.exit(1)
    lockfd = lock.fileno()
    readypipe, readypipeinfd = os.pipe()

    timeout = -1
    profile = False
    xmlrpcinterface = (None, '0')

    # Replace standard fds with our own
    with open('/dev/null', 'r') as si:
        os.dup2(si.fileno(), sys.stdin.fileno())

    so = open(logfile, 'a+')
    sys.stdout = Tee(sys.stdout, so)

    # Have stdout and stderr be the same so log output matches chronologically
    # and there aren't two seperate buffers
    sys.stderr = sys.stdout

    logger = logging.getLogger("BitBake")
    # Ensure logging messages get sent to the UI as events
    handler = bb.event.LogHandler()
    logger.addHandler(handler)

    bb.server.process.execServer(lockfd, readypipeinfd, lockname, sockname, timeout, xmlrpcinterface, profile)
    os.close(readypipe)


if __name__ == '__main__':
    args = parse_args()

    build = os.path.abspath(os.path.expanduser(args.build))
    if not os.path.exists(build):
        print("build dir does not exist", file=sys.stderr)
        sys.exit(1)

    run(build)
