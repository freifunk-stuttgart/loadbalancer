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
__updated__ = '2021-05-29'

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
    logging.debug("Getting vnstat...")
    vnstat = json.loads(subprocess.check_output(['/usr/bin/vnstat', '-h', '--json','--iface',iface]).decode('utf-8'))
    #with open('/home/leonard/freifunk/FfsScripts/vnstat.json','r') as fp:
    #    vnstat = json.load(fp)
    hours = vnstat['interfaces'][0]['traffic']['hours']
    data_hour = vnstat['interfaces'][0]['updated']['time']['hour']
    data_minute = vnstat['interfaces'][0]['updated']['time']['minutes']
    peak = 0

    try:
        # get current traffic (based on last 5 seconds)
        vnstat = json.loads(subprocess.check_output(['/usr/bin/vnstat', '-tr', '--json','--iface',iface]).decode('utf-8'))
        current_tx = vnstat['tx']['bytespersecond'] * 3600/1024
    except:
        current_tx = 0    # e.g. old version of vnstat doesn't support json output here

    if data_minute > 5 and hours[data_hour]['tx'] > 0:
        hours[data_hour]['tx'] *= 60/data_minute    # current hour contains data of less than 60 minutes
    else:
        hours[data_hour]['tx'] = current_tx    # use current traffic instead

    for h in hours:
        if h['tx'] > peak:
            peak = h['tx']

    expected_tx = 2*hours[(data_hour+23)%24]['tx'] - hours[(data_hour+22)%24]['tx']
    reference_tx = 2*hours[(data_hour+1)%24]['tx'] - hours[(data_hour+2)%24]['tx']

    if hours[data_hour]['tx'] > expected_tx:
        expected_tx = hours[data_hour]['tx']

    peak *= expected_tx/reference_tx    # traffic related to 24 hours ago
    if peak < hours[data_hour]['tx']:
        peak = hours[data_hour]['tx']

    peak_mbits = 8*peak/1024/3600
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
