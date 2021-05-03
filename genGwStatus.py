#!/usr/bin/python3
# encoding: utf-8
'''
genGwStatus -- generator for gwstatus.json
'''

import sys
import os
import time
import json
import subprocess
import logging
import dns.zone
import dns.query

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.1
__date__ = '2017-09-03'
__updated__ = '2021-05-01'

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


def getPeak():
    logging.debug("Getting uptime...")
    up_minutes = 0
    with open('/proc/uptime','r') as upfile:
        up_minutes  = int(float(upfile.read().split()[0]) / 60)

    logging.debug("Getting vnstat...")
    vnstat = json.loads(subprocess.check_output(['/usr/bin/vnstat', '-h', '--json','--iface',iface]).decode('utf-8'))
    #with open('/home/leonard/freifunk/FfsScripts/vnstat.json','r') as fp:
    #    vnstat = json.load(fp)
    hours = vnstat['interfaces'][0]['traffic']['hours']
    current_hour = int(time.strftime('%H'))
    current_minute = int(time.strftime('%M'))
    past_hours = int((up_minutes-current_minute+59)/60)
    peak  = 0

    if up_minutes >= 1440:    # Uptime >= 24 hours
        for h in hours:
            if h['tx'] > peak:
                peak = h['tx']
    else:
        start_hour = current_hour - past_hours

        if start_hour < 0:
            for id in range(start_hour+24, 24):
                if hours[id]['tx'] > peak:
                    peak = hours[id]['tx']
            start_hour = 0

        for id in range(start_hour, current_hour):
            if hours[id]['tx'] > peak:
                peak = hours[id]['tx']

    if past_hours == 1:    # GW got online during last hour
        peak *= 60 / (up_minutes - current_minute)    # correction for incomplete last hour

    # data of current hour is summed up to last update only
    data_minute = vnstat['interfaces'][0]['updated']['time']['minutes']
    if data_minute > 0:
        data_hour = vnstat['interfaces'][0]['updated']['time']['hour']
        current_tx = hours[data_hour]['tx']*60/data_minute
        if current_tx > peak:
            peak = current_tx

    peak_mbits = 8*peak/1024/3600

    # get current traffic (last 5 seconds)
    try:
        vnstat = json.loads(subprocess.check_output(['/usr/bin/vnstat', '-tr', '--json','--iface',iface]).decode('utf-8'))
        current_tx = vnstat['tx']['bytespersecond'] * 8/1024/1024
    except:
        current_tx = 0    # e.g. on old version of vnstat doesn't support json on output
    else:
        if current_tx > peak_mbits:
            peak_mbits = current_tx

    logging.debug("Found peak '{}'...".format(peak_mbits))
    return peak_mbits


class GatewayZone(object):
    def __init__(self):
        self._zone = dns.zone.from_xfr(dns.query.xfr('dns1.lihas.de', 'gw.freifunk-stuttgart.de'))

    def getDnsStatus(self, gwid, segment):
        hostname = 'gw%02is%02i'%(gwid, segment)
        try:
            record = self._zone.find_node(hostname, create=False)
            return 1
        except:
            return 0

def getPreference(bwlimit):
    preference = int((bwlimit-getPeak()) / (bwlimit/100.))
    return preference

def genData(segmentCount, preference=0):
    data = {}
    data['version'] = '1'
    data['timestamp'] = int(time.time())

    segments = {}
    gatewayZone = GatewayZone()
    for s in range(1,segmentCount+1):
        segments[s] = {}
        segments[s]['preference'] = preference
        segments[s]['dnsactive'] = gatewayZone.getDnsStatus(1, s)

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
