#!/usr/bin/python3
'''
Created on Sep 5, 2017

@author: leonard
'''

import subprocess
import re
import requests
import json
import socket
import os
import logging

logging.basicConfig(level=logging.DEBUG)

def getAvailableGwFromDns():
    cmd = "/usr/bin/dig -t axfr gw.freifunk-stuttgart.de @dns1.lihas.de"
    zone = subprocess.check_output(cmd.split(" ")).decode("utf-8")
    gw = {}
    p = re.compile('gw0[0-9]n[0-9][0-9]\.gw\.freifunk-stuttgart\.de')
    for line in zone.split("\n"):
        m = p.match(line)
        if m != None:
            gw[m.group()] = {}
    return gw

def getIpFromGwAndNum(gw,num):
    return "10.191.255.%i%i"%(gw,num)

def getGwAndNumFromGw(gw):
    p = re.compile("gw([0-9]{2})n([0-9]{2})")
    match = p.match(gw)
    gw = int(match.group(1))
    num = int(match.group(2))
    return (gw,num)

def getGwFromGwAndNum(gw,num):
    return "gw%sn%s"%(str(gw).zfill(2),str(num).zfill(2))

def getIpFromGw(gw):
    (gw,num) = getGwAndNumFromGw(gw)
    return getIpFromGwAndNum(gw,num)

def getGwNumFromBatctlLine(line):
    #alternative expression von are
    #sed 's/^.*:0*\([0-9]\+\):0*\([0-9]\+\)$/10.191.255.\1\2/'    
    p = re.compile("\ *02:[0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]([0-9]):[0-9]([0-9]).*")
    match = p.match(line)
    gw = int(match.group(1))
    num = int(match.group(2))
    return (gw,num)

def getIpFromBatctlLine(line):
    (gw,num) = getGwNumFromBatctlLine(line)
    return getIpFromGwAndNum(gw,num)

def parseBatctlOutput(data):
    #  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit
    gws = {}
    for line in data.strip().split("\n"):
        (gw,num) = getGwNumFromBatctlLine(line)
        gw = getGwFromGwAndNum(gw,num)
        gws[gw] = {}
    return gws

def getAvailableGwFromBatctl():
    output = ""
    for i in range(1,32+1):
        seg = ("%i"%(i)).zfill(2)
        BATCTL = "/usr/sbin/batctl"
        if os.path.isfile(BATCTL):
            cmd = "%s -m bat%s gwl -H -n"%(seg)
            output += subprocess.check_output(cmd.split(" ")).decode("utf-8")
        else:
            with open("tests/batctl-gwl.txt","r") as fp:
                output += fp.read()
    gws = parseBatctlOutput(output)
    gws = addSelfToGws(gws)
    return gws

def getAllStatus(gws):
    for gw in gws.keys():
        gws[gw] = getGwStatus(gw)
    return gws

def getGwStatus(hostname):
    fqdn = "%s.gw.freifunk-stuttgart.de"%(hostname)

    url = 'http://%s/data/gwstatus.json'%(fqdn)
    try:
        logging.debug("Downloading stats for {}".format(hostname))
        r = requests.get(url, timeout=1)
    except Exception as e:
        print(e)
        return {}
    
    if r.status_code == 404 or r.status_code == 503:
        print("Could not get Data for %s"%(hostname))
        return {}    
    
    text = r.text
    try:
        data = json.loads(text)
    except:
        logging.error("Error while loading json from %s with code %i"%(hostname,r.status_code))
        raise
    return data
    

def getPrefPerSegment(gws):
    segments = {}
    for gw in gws:
        g = gws[gw]
        if "segments" in g:
            for s in g["segments"]:
                if s not in segments:
                    segments[s] = {}
                segments[s][gw.split(".")[0]] = g["segments"][s]
    
    return segments
    
def getActiveGw(gws):
    active = 0
    for gw in gws:
        if gws[gw]["dnsactive"] == 1:
            active+=1
    return active

def getActiveGwPerSegmentFromDns():
    cmd = "/usr/bin/dig -t axfr gw.freifunk-stuttgart.de @dns1.lihas.de"
    zone = subprocess.check_output(cmd.split(" ")).decode("utf-8")
    segments = {}
    p = re.compile('gw0[0-9]s[0-6][0-9]\.gw\.freifunk-stuttgart\.de')
    
    for line in zone.split("\n"):
        m = p.match(line)
        if m != None:
            segment = int(m.group()[5:7])
            gw = int(m.group()[2:4])
            #print(m.group())
            #print(segment)
            if not segment in segments:
                segments[segment] = {}
            segments[segment][gw] = None
    return segments

def decide(segments):
    dnsActivePerSegment = getActiveGwPerSegmentFromDns()
    for segment in segments:
        s = segments[segment]
        dnsActive = len(dnsActivePerSegment[int(segment)])
        logging.debug("GWs DNS active in Segment %s: %i"%(segment,dnsActive))
        logging.debug("In Segment %s sind %i GWs aktiv"%(segment, getActiveGw(s)))
        logging.debug(s[localhost]["preference"])
        preference = s[localhost]["preference"]
        dnsactive = s[localhost]["dnsactive"]
        if dnsactive and preference < 30:
            logging.info("Remove this gw from DNS for segment %s"%(segment))
        elif (preference > 35 or dnsActive < 2)and not dnsactive:
            logging.info("Add this gw to DNS for segment %s"%(segment))
        else:
            pass 
            #print("No change needed for segment %s"%(segment))

def addSelfToGws(gws):
    localhost = socket.gethostname()
    if not localhost.startswith("gw"):
        localhost = "gw01n03"
    gws[localhost] = {}
    return gws

if __name__ == '__main__':
    localhost = socket.gethostname()
    if localhost == "littleblue":
        localhost = "gw01n03"
    gws = getAvailableGwFromBatctl()

    gws = getAllStatus(gws)
    segments = getPrefPerSegment(gws)
    decide(segments)
