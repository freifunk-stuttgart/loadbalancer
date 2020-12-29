import unittest
from gwLoadBalancer import *

class gwLoadBalancerTestCase(unittest.TestCase):
    def test_getIpFromGwAndNum(self):
        ip = getIpFromGwAndNum(1,3)
        self.assertEqual(ip,"10.191.255.13")

    def test_getGwAndNumFromGw(self):
        (gw,num) = getGwAndNumFromGw("gw01n03")
        self.assertEqual(gw,1)
        self.assertEqual(num,3)

    def test_getGwFromGwAndNum(self):
        self.assertEqual(getGwFromGwAndNum(1,3),"gw01n03")

    def test_getGwNumFromBatctlLine(self):
        line = '  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit'
        (gw,num) = getGwNumFromBatctlLine(line)
        self.assertEqual(gw, 7)
        self.assertEqual(num,1)

    def test_getIpFromBatctlLine(self):
        line = '  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit'
        ip = getIpFromBatctlLine(line)
        self.assertEqual(ip,"10.191.255.71")

    def test_parseBatctlOutput(self):
        data = """  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit
  02:00:35:01:04:01 (255) 02:00:35:01:04:01 [      bb01]: 64.0/64.0 MBit
  02:00:35:01:05:03 (255) 02:00:35:01:05:03 [      bb01]: 64.0/64.0 MBit
  02:00:38:01:04:03 (255) 02:00:35:01:04:03 [      bb01]: 64.0/64.0 MBit
  02:00:38:01:09:02 (255) 02:00:35:01:09:02 [      bb01]: 64.0/64.0 MBit"""
        gws = parseBatctlOutput(data)
        #expextedGws = ["10.191.255.71","10.191.255.41","10.191.255.53","10.191.255.43","10.191.255.92"]
        expextedGws = ["gw07n01","gw04n01","gw05n03","gw04n03","gw09n02"]
        self.assertEqual(list(gws.keys()),expextedGws)

    def test_getAvailableGwFromBatctl(self):
        gws = getAvailableGwFromBatctl()
        #expextedGws = ["10.191.255.71", "10.191.255.41", "10.191.255.53", "10.191.255.43", "10.191.255.92"]
        expextedGws = ["gw07n01","gw04n01","gw05n03","gw04n03","gw09n02","gw01n03"]
        self.assertEqual(list(gws.keys()), expextedGws)

    def test_getGwStatus(self):
        data = getGwStatus("gw01n03")
        self.assertEqual(data["version"],"1")

    def test_addSelfToGws(self):
        gws = {}
        addSelfToGws(gws)
        self.assertEqual(gws,{"gw01n03": {}})