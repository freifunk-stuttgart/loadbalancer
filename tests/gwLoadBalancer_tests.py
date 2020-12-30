import unittest
from gwLoadBalancer import *

class gwLoadBalancerTestCase(unittest.TestCase):
    def test_getIpFromGwAndNum(self):
        lb = GwLoadBalancer()
        ip = lb.getIpFromGwAndNum(1,3)
        self.assertEqual(ip,"10.191.255.13")

    def test_getGwAndNumFromGw(self):
        lb = GwLoadBalancer()
        (gw,num) = lb.getGwAndNumFromGw("gw01n03")
        self.assertEqual(gw,1)
        self.assertEqual(num,3)

    def test_getGwFromGwAndNum(self):
        lb = GwLoadBalancer()
        self.assertEqual(lb.getGwFromGwAndNum(1,3),"gw01n03")

    def test_getIpFromGw(self):
        lb = GwLoadBalancer()
        self.assertEqual(lb.getIpFromGw("gw01n03"),"10.191.255.13")

    def test_getGwNumFromBatctlLine(self):
        lb = GwLoadBalancer()
        line = '  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit'
        (gw,num) = lb.getGwNumFromBatctlLine(line)
        self.assertEqual(gw, 7)
        self.assertEqual(num,1)

    def test_getIpFromBatctlLine(self):
        lb = GwLoadBalancer()
        line = '  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit'
        ip = lb.getIpFromBatctlLine(line)
        self.assertEqual(ip,"10.191.255.71")

    def test_parseBatctlOutput(self):
        lb = GwLoadBalancer()
        data = """  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit
  02:00:35:01:04:01 (255) 02:00:35:01:04:01 [      bb01]: 64.0/64.0 MBit
  02:00:35:01:05:03 (255) 02:00:35:01:05:03 [      bb01]: 64.0/64.0 MBit
  02:00:38:01:04:03 (255) 02:00:35:01:04:03 [      bb01]: 64.0/64.0 MBit
  02:00:38:01:09:02 (255) 02:00:35:01:09:02 [      bb01]: 64.0/64.0 MBit"""
        gws = lb.parseBatctlOutput(data)
        #expextedGws = ["10.191.255.71","10.191.255.41","10.191.255.53","10.191.255.43","10.191.255.92"]
        expextedGws = ["gw07n01","gw04n01","gw05n03","gw04n03","gw09n02"]
        self.assertEqual(list(gws.keys()),expextedGws)

    def test_getAvailableGwFromBatctl(self):
        lb = GwLoadBalancer()
        gws = lb.getAvailableGwFromBatctl()
        #expextedGws = ["10.191.255.71", "10.191.255.41", "10.191.255.53", "10.191.255.43", "10.191.255.92"]
        expextedGws = ["gw07n01","gw04n01","gw05n03","gw04n03","gw09n02","gw01n03"]
        self.assertEqual(list(gws.keys()), expextedGws)

    def test_addSelfToGws(self):
        lb = GwLoadBalancer()
        gws = {}
        lb.addSelfToGws(gws)
        self.assertEqual(gws,{"gw01n03": {}})

    def test_getGwStatusUrl(self):
        lb = GwLoadBalancer()
        url = lb.getGwStatusUrl("gw01n03")
        self.assertEqual("http://10.191.255.13/data/gwstatus.json",url)
        lb.use_backbone = False
        url = lb.getGwStatusUrl("gw01n03")
        self.assertEqual("http://gw01n03.gw.freifunk-stuttgart.de/data/gwstatus.json",url)

    def test_getGwStatus(self):
        lb = GwLoadBalancer()
        lb.use_backbone = False
        data = lb.getGwStatus("gw01n03")
        self.assertEqual(data["version"],"1")

    def test_getAllStatus(self):
        lb = GwLoadBalancer()
        lb.use_backbone = False
        lb.getAllStatus({"gw01n03": {}})
        #self.assertEqual(lb.status["segments"]["gw01n03"]["1"]["preference"],19)
        #self.assertIn("preference",lb.status["1"]["gw01n03"]["1"])

    def test_printStatus(self):
        lb = GwLoadBalancer()
        lb.use_backbone = False
        lb.getAllStatus({"gw01n03": {}})
        lb.status({})
        lb.printStatus()
