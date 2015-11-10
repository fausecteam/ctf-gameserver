#!/usr/bin/python3
#
# set $PYTHONPATH to your local ctflib/flags checkout
#
# If you want to test subsequent runs, you really want to set
# --first. An perfectly fine value for that is `date +"%s"`
#
#   for i in {1..10}
#   do
#     ./testrunner.py --first 1437258032 --backend `mktemp -d` --tick $i --ip $someip --team 1 --service 1 dummy:DummyChecker
#   done

import time
from subprocess import Popen, PIPE
import argparse
import flag
import codecs
import sys
import importlib
import logging

def run_job(args):
    logging.debug("Importing checker")
    checkermod, checkerclass = args.checker.split(":")
    checkermod = importlib.import_module(checkermod)
    checkerclass = getattr(checkermod, checkerclass)

    logging.debug("Initializing checker")
    checker = checkerclass(args.tick, args.team, args.service, args.ip)
    checker.set_starttime(args.first)
    checker.set_backend(args.backend)

    logging.debug("Running checker")
    result = checker.run()

    if 0 == result:
        print("OK")
    elif 1 == result:
        print("TIMEOUT")
    elif 2 == result:
        print("NOTWORKING")
    elif 3 == result:
        print("NOTFOUND")

def main():
    logging.basicConfig()
    parser = argparse.ArgumentParser(description="CTF checker runner")
    parser.add_argument('checker', type=str,
                        help="module:classname of checker")
    parser.add_argument('--verbose', action="store_true")
    parser.add_argument('--ip', type=str, required=True)
    parser.add_argument('--tick', type=int, required=True)
    parser.add_argument('--team', type=int, required=True)
    parser.add_argument('--service', type=int, required=True)
    parser.add_argument('--first', type=int, default=int(time.time()) // 60 * 60,
                        help="timestamp of first tick")
    parser.add_argument('--backend', type=str, default='/tmp',
                        help='location to store persistent data')
    parser.add_argument('-v', '--loglevel', default='WARNING', type=str,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Loglevel')

    args = parser.parse_args()

    numeric_level = getattr(logging, args.loglevel.upper())
    logging.getLogger().setLevel(numeric_level)

    logging.debug(repr(args))
    starttime = time.time()
    run_job(args)
    logging.info("Processing took %.2f seconds" % (time.time() - starttime,))

if __name__ == '__main__':
    main()
