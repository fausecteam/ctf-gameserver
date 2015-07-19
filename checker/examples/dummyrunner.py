#!/usr/bin/python3

import sys
import time
import os
import codecs

def generate_flag(tick, payload=None):
    if payload is None:
        sys.stdout.write("FLAG %d\n" % (tick,))
    else:
        sys.stdout.write("FLAG %d %s\n" % (tick, codecs.encode(os.urandom(8), 'hex').decode('latin-1')))
    sys.stdout.flush()
    return sys.stdin.readline().strip()

def place_flag(flag, ip):
    return 0

def check_for_flag(flag, ip):    
    return 0

def main(tick, ip):
    result = place_flag(generate_flag(tick), ip)
    if 0 != result:
        sys.exit(result)

    oldesttick = max(tick-7, -1)
    for ctick in range(tick-1, oldesttick, -1):
        result = check_for_flag(generate_flag(ctick), ip)
        if 0 != result:
            sys.exit(result)

    sys.exit(0)
        
if __name__ == '__main__':
    _, tick, ip = sys.argv
    main(tick=int(tick), ip=ip)
