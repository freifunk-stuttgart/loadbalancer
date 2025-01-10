#!/usr/bin/python3
# encoding: utf-8
'''
genGwStatus -- generator for gwstatus.json
'''

import sys
import os
import time
import calendar
import json
import subprocess
import logging
import dns.zone
import dns.query
import socket

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.1
__date__ = '2017-09-03'
__updated__ = '2022-04-30'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = 'E: %s' % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg


def getUnixTime(data):
    t = time.strptime('%4d-%02d-%02d %02d:%02d' %
                      ( data['date']['year'],
                        data['date']['month'],
                        data['date']['day'],
                       data['time']['hour'],
                       data['time']['minute']
                     ),'%Y-%m-%d %H:%M')

    return calendar.timegm(t)


def getPeak_v1(vnstat):
    peak = 0

    for h in vnstat['interfaces'][0]['traffic']['hours']:
        if h['tx'] > peak:
            peak = h['tx']

    peak_mbits = peak*8/60/60/1024
    return peak_mbits


def getPeak_v2(vnstat):
    start_time = getUnixTime(vnstat['interfaces'][0]['updated']) - 24*3600
    peak = 0

    for h in vnstat['interfaces'][0]['traffic']['hour']:
        t = getUnixTime(h)

        if t >= start_time and h['tx'] > peak:
            peak = h['tx']

    start_time = getUnixTime(vnstat['interfaces'][0]['updated'])
    start_hour = start_time - 3600
    start_quarter = start_time - 900

    traffic = 0
    intervals = 0

    for f in vnstat['interfaces'][0]['traffic']['fiveminute']:
        t = getUnixTime(f)

        if t >= start_hour:
            traffic += f['tx']
            intervals += 1

            if t >= start_quarter and f['tx']*12 > peak:
                peak = f['tx']*12

    if intervals > 0:
        traffic = int(traffic * 12 / intervals)

        if traffic > peak:
            peak = traffic

    peak_mbits = peak*8/60/60/1024/1024
    return peak_mbits


def getPeak():
    logging.debug("Getting vnstat...")
    vnstat = json.loads(subprocess.check_output(['/usr/bin/vnstat', '-h', '--json','--iface',iface]).decode('utf-8'))
    #with open('/home/leonard/freifunk/FfsScripts/vnstat.json','r') as fp:
    #    vnstat = json.load(fp)

    if vnstat['jsonversion'] == '1':
        peak_mbits = getPeak_v1(vnstat)
    elif vnstat['jsonversion'] == '2':
        peak_mbits = getPeak_v2(vnstat)
    else:
        logging.debug("Unknown json version")
        sys.exit(0)

    logging.debug("Found peak '{}'...".format(peak_mbits))
    return peak_mbits

def getPreference(bwlimit):
    preference = int((bwlimit-getPeak()) / (bwlimit/100.))
    return preference


def genData(segmentCount, preference=0):
    data = {}
    data['version'] = '1'
    data['timestamp'] = int(time.time())

    segments = {}
    for s in range(1,segmentCount+1):
        segments[s] = {}
        segments[s]['preference'] = preference

    data['segments'] = segments
    return data


def genJson(data,output):
    with open(output,'w') as fp:
        json.dump(data,fp ,indent=4,separators=(',', ': '))


#def main(argv=None): # IGNORE:C0111
if __name__ == '__main__':

    # Setup argument parser
    parser = ArgumentParser(description='Generator for gwstats.json', formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('-o', '--output', dest='output', action='store', required=True, help='output filename')
    parser.add_argument('-b', '--bwlimit', type=int, required=True, help='bwlimit in mbit/s')
    parser.add_argument('-s', '--segments', type=int, required=True, help='number of segments to handle')
    parser.add_argument('-i', '--iface', type=str, required=True, help='interface for vnstat')
    parser.add_argument('-d', '--debug', action='store_true', help='print debug/logging information')

    # Process arguments
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    bwlimit = args.bwlimit
    segmentCount = args.segments
    iface = args.iface

    preference = getPreference(bwlimit)
    data = genData(segmentCount, preference=preference)
    genJson(data,args.output)
