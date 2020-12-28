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

def getAvailableGw():
    cmd = "/usr/bin/dig -t axfr gw.freifunk-stuttgart.de @dns1.lihas.de"
    zone = subprocess.check_output(cmd.split(" ")).decode("utf-8")
    gw = {}
    p = re.compile('gw0[0-9]n[0-9][0-9]\.gw\.freifunk-stuttgart\.de')
    
    for line in zone.split("\n"):
        m = p.match(line)
        if m != None:
            gw[m.group()] = {}
                        
    return gw

def getAllStatus(gws):
    for gw in gws.keys():
        gws[gw] = getGwStatus(gw)
    return gws

def getGwStatus(hostname):
    url = 'http://%s/data/gwstatus.json'%(hostname)
    try:
        r = requests.get(url, timeout=1)
    except:
        return {}
    
    if r.status_code == 404 or r.status_code == 503:
        return {}    
    
    text = r.text
    try:
        data = json.loads(text)
    except:
        print("Error while loading json from %s with code %i"%(hostname,r.status_code))
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
        #print("GWs DNS active in Segment %s: %i"%(segment,dnsActive))
        #print("In Segment %s sind %i GWs aktiv"%(segment, getActiveGw(s)))
        #print (s[localhost]["preference"])
        preference = s[localhost]["preference"]
        dnsactive = s[localhost]["dnsactive"]
        if dnsactive and preference < 30:
            print("Remove this gw from DNS for segment %s"%(segment))
        elif (preference > 35 or dnsActive < 2)and not dnsactive:
            print("Add this gw to DNS for segment %s"%(segment))
        else:
            pass 
            #print("No change needed for segment %s"%(segment))
            


if __name__ == '__main__':
    localhost = socket.gethostname()
    if localhost == "littleblue":
        localhost = "gw01n03"
    print(localhost)
    gws = getAvailableGw()
    gws = getAllStatus(gws)
    segments = getPrefPerSegment(gws)
    decide(segments)