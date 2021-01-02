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
import sys
import time
import argparse
import logging

logging.basicConfig(level=logging.ERROR)

class GwLoadBalancer:
    def __init__(self):
        self.use_backbone = True
        self.status = {}
        self.desiredGwPerSegment = 2
        self.allGws = {}
        self.localhost = socket.gethostname()
        self.target = self.localhost
        self.segments = 32
        self.maxAgeInSeconds = 60*15 # 15 minutes

    def dnsZoneTransfer(self):
        cmd = "/usr/bin/dig -t axfr gw.freifunk-stuttgart.de @dns1.lihas.de"
        self.zoneData = subprocess.check_output(cmd.split(" ")).decode("utf-8")

    def getAvailableGwFromDns(self):
        gw = self.allGws
        p = re.compile('(gw0[0-9]n0[0-9])\.gw\.freifunk-stuttgart\.de')
        for line in self.zoneData.split("\n"):
            m = p.match(line)
            if m != None:
                gw[m.group(1)] = {}
        self.allGws = gw

    def getIpFromGwAndNum(self,gw,num):
        return "10.191.255.%i%i"%(gw,num)

    def getGwAndNumFromGw(self,gw):
        p = re.compile("gw([0-9]{2})n([0-9]{2})")
        match = p.match(gw)
        gw = int(match.group(1))
        num = int(match.group(2))
        return (gw,num)

    def getGwFromGwAndNum(self,gw,num):
        return "gw%sn%s"%(str(gw).zfill(2),str(num).zfill(2))

    def getIpFromGw(self,gw):
        (gw,num) = self.getGwAndNumFromGw(gw)
        return self.getIpFromGwAndNum(gw,num)

    def getGwNumFromBatctlLine(self,line):
        #alternative expression von are
        #sed 's/^.*:0*\([0-9]\+\):0*\([0-9]\+\)$/10.191.255.\1\2/'
        p = re.compile("\ *02:[0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]([0-9]):[0-9]([0-9]).*")
        match = p.match(line)
        gw = int(match.group(1))
        num = int(match.group(2))
        return (gw,num)

    def getIpFromBatctlLine(self,line):
        (gw,num) = self.getGwNumFromBatctlLine(line)
        return self.getIpFromGwAndNum(gw,num)

    def parseBatctlOutput(self,data):
        # example:
        #  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit
        for line in data.strip().split("\n"):
            (gw,num) = self.getGwNumFromBatctlLine(line)
            gw = self.getGwFromGwAndNum(gw,num)
            self.allGws[gw] = {}

    def getAvailableGwFromBatctl(self):
        output = ""
        for i in range(1,self.segments+1):
            seg = ("%i"%(i)).zfill(2)
            BATCTL = "/usr/sbin/batctl"
            if os.path.isfile(BATCTL):
                cmd = "%s -m bat%s gwl -H -n"%(BATCTL,seg)
                output += subprocess.check_output(cmd.split(" ")).decode("utf-8")
            else:
                with open("tests/batctl-gwl.txt","r") as fp:
                    output += fp.read()
        self.parseBatctlOutput(output)
        self.addSelfToGws()

    def addSelfToGws(self):
        if self.localhost.startswith("gw"):
            self.allGws[self.localhost] = {}

    def getGwStatusUrl(self,gw):
        if self.use_backbone:
            fqdn = self.getIpFromGw(gw)
        else:
            fqdn = "%s.gw.freifunk-stuttgart.de"%(gw)
        return 'http://%s/data/gwstatus.json'%(fqdn)

    def getGwStatus(self, gw):
        url = self.getGwStatusUrl(gw)
        try:
            r = requests.get(url, timeout=1)
        except Exception as e:
            return {}
        if r.status_code == 404 or r.status_code == 503:
            logging.info("Could not get Data for %s" % (gw))
            return {}
        text = r.text
        if len(text) == 0:
            logging.warning("GW %s returns empty document"%(gw))
            return {}
        try:
            data = json.loads(text)
        except Exception as e:
            logging.warning(e)
            logging.warning("Error while loading json from %s with code %i" % (gw, r.status_code))
            raise
        return data

    def validateGwStatus(self,gw,status):
        local_timestamp = time.time()
        result = True
        if (local_timestamp - status["timestamp"]) > self.maxAgeInSeconds:
            logging.warning("Rejecting gwstatus from %s as it is too old!"%(gw))
            result = False
        for (segment,data) in status["segments"].items():
            dnsactive = data["dnsactive"]
            active = self.getActiveGwPerSegmentFromDns(segment = segment)
            if dnsactive == 1 and gw not in active:
                logging.warning("DNS status for %s in segment %s: Reports dnsactive==1 but is not active!"%(gw,segment))
                result = False
            if dnsactive == 0 and gw in active:
                logging.warning("DNS status for %s in segment %s: Reports dnsactive==0 but is active!"%(gw,segment))
                result = False
        return result

    def getAllStatus(self):
        for gw in self.allGws.keys():
            self.allGws[gw] = self.getGwStatus(gw)

    def getStatus(self):
        for (gw,gwstatus) in self.allGws.items():
            if gwstatus == {}:
                continue
            if not self.validateGwStatus(gw,gwstatus):
                gwstatus = {}
                continue
            for segment in gwstatus["segments"]:
                if segment not in self.status:
                    self.status[segment] = {}
                self.status[segment][gw] = gwstatus["segments"][segment]

    def getAllGwsInSegment(self,segment):
        segmentstatus = self.status[segment]
        return sorted((gw for gw in segmentstatus))

    def getBestGwForSegment(self,segment):
        segmentstatus = self.status[segment]
        result = sorted(((segmentstatus[gw]["preference"],gw) for gw in segmentstatus), reverse=True)[0:self.desiredGwPerSegment]
        return sorted(x[1] for x in result)

    def getGwsWithDnsactiveEqualTo(self,segment,desiredStatus):
        segmentstatus = self.status[segment]
        return sorted((gw for gw in segmentstatus if segmentstatus[gw]["dnsactive"] == desiredStatus))

    def getGwsThatHaveToBeAddedToDns(self,segment):
        gwsThatHaveToBeInDns = set(self.getBestGwForSegment(segment))
        gwsNotInDns = set(self.getGwsWithDnsactiveEqualTo(segment,0))
        gwsThatHaveToBeAddedToDns = (gwsThatHaveToBeInDns.intersection(gwsNotInDns))
        return sorted(gwsThatHaveToBeAddedToDns)

    def getGwsThatHaveToRemovedFromDns(self,segment):
        gwsThatHaveToBeInDns = set(self.getBestGwForSegment(segment = segment))
        gwsInDns = set(self.getGwsWithDnsactiveEqualTo(segment = segment,desiredStatus = 1))
        allGws = self.getAllGwsInSegment(segment = segment)
        gwsThatHaveNotToBeInDns = set(allGws).symmetric_difference(gwsThatHaveToBeInDns).intersection(gwsInDns)
        return sorted(gwsThatHaveNotToBeInDns)

    def getResult(self):
        result = ""
        self.commands_all = []
        self.commands_local = []
        if self.target != None:
            target = self.target
        else:
            target = self.localhost
        for segment in self.status:
            gwsThatHaveToBeAddedToDns = self.getGwsThatHaveToBeAddedToDns(segment)
            getGwsThatHaveToRemovedFromDns = self.getGwsThatHaveToRemovedFromDns(segment)
            if len(gwsThatHaveToBeAddedToDns) > 0:
                result += "GWs that have to be added in Segement %s to dns: %s\n"%(segment," ".join(gwsThatHaveToBeAddedToDns))
                for gw in gwsThatHaveToBeAddedToDns:
                    command = self.gen_nsupdate(gw,segment,"add")
                    self.commands_all += command
                    if gw == self.target:
                        self.commands_local += command
            if len(getGwsThatHaveToRemovedFromDns) > 0 and len(gwsThatHaveToBeAddedToDns) == 0:
                result += "GWs that have to be removed in Segement %s from dns: %s\n"%(segment," ".join(getGwsThatHaveToRemovedFromDns))
                for gw in getGwsThatHaveToRemovedFromDns:
                    command = self.gen_nsupdate(gw,segment,"delete")
                    self.commands_all += command
                    if gw == self.target:
                        self.commands_local += command

            if len(result) ==0:
                result = "All is fine!"
        return result

    def getIpToGwLookup(self):
        self.reverseDnsEntries = {}
        p1 = re.compile('(gw0[0-9]n0[0-9])\.gw\.freifunk-stuttgart\.de\. [0-9]+ IN A*\t(.*)')
        for line in self.zoneData.split("\n"):
            m = p1.match(line)
            if m != None:
                hostname = m.group(1)
                ip = m.group(2)
                self.reverseDnsEntries[ip] = hostname

    def getActiveGwPerSegmentFromDns(self,segment):
        gws = []
        zone = self.zoneData
        segments = {}
        p = re.compile('(gw0[0-9])s([0-9]{2})\.gw\.freifunk-stuttgart\.de\. [0-9]+ IN A*\t(.*)')
        for line in zone.split("\n"):
            m = p.match(line)
            if m != None:
                s = str(int(m.group(2)))
                gwCluster = m.group(1)
                ip = m.group(3)
                if s == segment and s != "99":
                    try:
                        gw = self.reverseDnsEntries[ip]
                    except Exception as e:
                        logging.error("NO entry for GWCluster %s and IP %s"%(gwCluster,ip))
                        raise
                    if gw not in gws:
                        gws.append(gw)
        return gws

    def validateStatus(self):
        result = True
        for (segment,data) in self.status.items():
            activeGw = set(self.getGwsWithDnsactiveEqualTo(segment = segment, desiredStatus = 1))
            activeGwDns = set(self.getActiveGwPerSegmentFromDns(segment = segment))
            if activeGw != activeGwDns:
                logging.warning("Segment %s setup is not as expected: %s vs. %s"%(segment,activeGw,activeGwDns))
            if not activeGw.issubset(activeGwDns):
                result = False
                logging.error("Segment %s setup is wrong: %s vs. %s"%(segment,activeGw,activeGwDns))
        return result

    def get_record_for_gw(self,gw,record):
        p = re.compile('(gw0[0-9]n0[0-9])\.gw\.freifunk-stuttgart\.de\. [0-9]+ IN %s\t(.*)'%(record))
        for line in self.zoneData.split("\n"):
            m = p.match(line)
            if m != None:
                hostname = m.group(1)
                ip = m.group(2)
                if hostname == gw:
                    return ip
        return None

    def gen_nsupdate(self,gw,segment,cmd):
        lines = []
        for record_type in ("A","AAAA"):
            ip = self.get_record_for_gw(gw,record_type)
            if ip != None:
                s = "%ss%s"%(gw[0:4],segment.zfill(2))
                line = "update %s %s.gw.freifunk-stuttgart.de. 300 %s %s"%(cmd,s,record_type,ip)
                lines.append(line)
        return lines

    def run(self):
        self.dnsZoneTransfer()
        self.getIpToGwLookup()
        localhost = socket.gethostname()
        if localhost.startswith("gw"):
            self.getAvailableGwFromBatctl()
        else:
            self.use_backbone = False
            self.getAvailableGwFromDns()
        self.getAllStatus()
        self.getStatus()
        if not self.validateStatus():
            logging.error("Status is not consitent, bye!")
            sys.exit(1)
        report = self.getResult()
        logging.info(report)

    def saveResult(self,output):
        with open(output,"w") as fp:
            fp.write(";generatet at %s\n"%(time.ctime()))
            if len(self.commands_local) > 0:
                fp.write("\n".join(self.commands_local))
                fp.write("\n")
                fp.write("send\n")
            else:
                fp.write(";nothing to do here this time...\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generator for nsupdate commands", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", dest="output", action="store", required=False, help="output filename")
    parser.add_argument("-t", "--target", dest="target", action="store", required=False, help="generate output for")
    parser.add_argument("-v", "--verbose", action="store_true", help="print warning/info information")
    args = parser.parse_args()

    lb = GwLoadBalancer()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    if args.target != None:
        lb.target = args.target
    lb.run()
    if args.output != None:
        lb.saveResult(args.output)
