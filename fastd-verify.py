#!/usr/bin/python3
'''
Created on Apr 29, 2021
@author: roland
'''

import os
import time
import argparse
import logging
import logging.handlers
import json

my_logger = logging.getLogger('fastd-verify')
my_logger.setLevel(logging.DEBUG)
log_handler = logging.handlers.SysLogHandler(address = '/dev/log')
my_logger.addHandler(log_handler)

DEFAULT_PREFERENCE = 50


def IsValidKey(FilePath, FastdKey):
    for FileName in os.listdir(FilePath):
        try:
            with open(os.path.join(FilePath, FileName), encoding = 'utf-8') as KeyFile:
                KeyData  = KeyFile.read()
        except:
            my_logger.error('fastd-verify: Error while reading KeyFile %s/%s' % (FilePath, FileName))
        else:
            if FastdKey in KeyData:
#                my_logger.debug('fastd-verify: FastdKey %s found in KeyFile %s/%s' % (FastdKey, FilePath, FileName))
                return True

    return False


def GetGwPreference(StatusFile, Segment):
    try:
        with open(StatusFile,'r') as JsonFile:
            StatusDict = json.load(JsonFile)
            Preference = int(StatusDict['segments'][str(Segment)]['preference'])

            if Preference > 80:
               Preference = 80
            elif Preference < 0:
                Preference = 0

    except:
        my_logger.error('fastd-verify: Error while checking GW StatusFile %s for Segment %d!' % (StatusFile, Segment))
        Preference = DEFAULT_PREFERENCE

    return Preference


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verification of Fastd Connection Requests',
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-k', '--keyfolder', dest='keyfolder', action='store', required=True, help='path to keyfiles')
    parser.add_argument('-g', '--gwstatus', dest='gwstatus', action='store', required=True, help='path to gwstatus.json')
    args = parser.parse_args()

    if 'INTERFACE' not in os.environ or 'PEER_KEY' not in os.environ:
        my_logger.error('fastd-verify: Error on Fastd API: Environment Variables not set!')
    else:
        if IsValidKey(args.keyfolder, os.environ['PEER_KEY'].lower()):
            Preference = GetGwPreference(args.gwstatus, int(os.environ['INTERFACE'][3:]))
            time.sleep((80 - Preference) * 0.08)
            exit(0)

exit(1)
