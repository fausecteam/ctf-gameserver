#!/usr/bin/python3
#
# set $PYTHONPATH to your local ctflib/flags checkout
#
# If you want to test subsequent runs, you really want to set
# --first. An perfectly fine value for that is `date +"%s"`
#
#   for i in {1..10}
#   do
#     ./testrunner.py --first 1437258032 --tick $i --ip $someip --team 1 --service 1 ./mychecker
#   done

import time
from subprocess import Popen, PIPE
import argparse
import flag
import codecs
import sys

def run_job(args):
    job = Popen([args.script, str(args.tick), args.ip], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    while job.poll() is None:
        line = job.stdout.readline().strip().split()
        if len(line) == 0:
            continue
        if args.verbose:
            sys.stderr.write(repr(line) + "\n")
        if line[0] == "FLAG":
            payload = None
            if len(line) > 2:
                payload = codecs.decode(line[2], 'hex')

            generatedflag = flag.generate(args.team, args.service, payload, args.first + args.duration *  int(line[1]))
            if args.verbose:
                sys.stderr.write(generatedflag + "\n")
            job.stdin.write(generatedflag)
            job.stdin.write("\n")
            job.stdin.flush()

    result = job.returncode
    if 0 == result:
        print("OK", repr(job.stderr.read()))
    elif 1 == result:
        print("TIMEOUT", repr(job.stderr.read()))
    elif 2 == result:
        print("NOTWORKING", repr(job.stderr.read()))
    elif 3 == result:
        print("NOTFOUND", repr(job.stderr.read()))

def main():
    parser = argparse.ArgumentParser(description="CTF checker runner")
    parser.add_argument('script', type=str,
                        help="Checker script to run")
    parser.add_argument('--verbose', action="store_true")
    parser.add_argument('--ip', type=str, required=True)
    parser.add_argument('--tick', type=int, required=True)
    parser.add_argument('--team', type=int, required=True)
    parser.add_argument('--service', type=int, required=True)
    parser.add_argument('--duration', type=int, default=120,
                        help="tick duration in seconds")
    parser.add_argument('--first', type=int, default=int(time.time()) // 60 * 60,
                        help="timestamp of first tick")
    
    args = parser.parse_args()
    if args.verbose:
        sys.stderr.write(str(args) + "\n")
    starttime = time.time()
    run_job(args)
    print("Processing took %.2f seconds" % (time.time() - starttime,))

if __name__ == '__main__':
    main()
