import unittest
import time
import tempfile
from gwLoadBalancer import *


class GwLoadBalancerTestCase(unittest.TestCase):
    def setUp(self):
        self.gwstatus = {
            "timestamp": 1609511049,
            "version": "1",
            "segments": {
                "1": {
                    "preference": 33,
                    "dnsactive": 1
                },
                "2": {
                    "preference": 33,
                    "dnsactive": 0
                }
            }
        }

        self.gwstatus["timestamp"] = int(time.time())

        self.status = {"1": {}, "2": {}}
        self.status["1"]["gw01n03"] = {"preference": 19, "dnsactive": 1}
        self.status["1"]["gw04n03"] = {"preference": 22, "dnsactive": 0}
        self.status["1"]["gw05n03"] = {"preference": 40, "dnsactive": 1}
        self.status["1"]["gw07n01"] = {"preference": 50, "dnsactive": 1}
        self.status["1"]["gw09n02"] = {"preference": 80, "dnsactive": 0}

        self.status["2"]["gw01n03"] = {"preference": 10, "dnsactive": 0}
        self.status["2"]["gw04n03"] = {"preference": 20, "dnsactive": 1}
        self.status["2"]["gw05n03"] = {"preference": 30, "dnsactive": 1}
        self.status["2"]["gw07n01"] = {"preference": 40, "dnsactive": 1}
        self.status["2"]["gw09n02"] = {"preference": 60, "dnsactive": 1}

        self.zoneData = """
gw01n03.gw.freifunk-stuttgart.de. 300 IN A	88.198.230.6
gw01n03.gw.freifunk-stuttgart.de. 300 IN AAAA	2a01:4f8:190:5205:260:2fff:fe08:13cd
gw04n03.gw.freifunk-stuttgart.de. 3600 IN A	138.201.55.210
gw04n03.gw.freifunk-stuttgart.de. 3600 IN AAAA	2a01:4f8:172:10ce::43
gw05n03.gw.freifunk-stuttgart.de. 300 IN A	93.186.197.153
gw05n03.gw.freifunk-stuttgart.de. 300 IN AAAA	2001:4ba0:ffff:150::1
gw07n01.gw.freifunk-stuttgart.de. 600 IN A	163.172.12.135
gw09n02.gw.freifunk-stuttgart.de. 600 IN A	212.227.213.45
gw09n02.gw.freifunk-stuttgart.de. 600 IN AAAA	2001:8d8:1801:35f::92

gw01s01.gw.freifunk-stuttgart.de. 300 IN AAAA	2a01:4f8:190:5205:260:2fff:fe08:13cd
gw01s01.gw.freifunk-stuttgart.de. 300 IN A	88.198.230.6
gw05s01.gw.freifunk-stuttgart.de. 300 IN AAAA	2001:4ba0:ffff:150::1
gw05s01.gw.freifunk-stuttgart.de. 300 IN A	93.186.197.153
gw07s01.gw.freifunk-stuttgart.de. 300 IN A	163.172.12.135

gw04s02.gw.freifunk-stuttgart.de. 300 IN A	138.201.55.210
gw04s02.gw.freifunk-stuttgart.de. 300 IN AAAA	2a01:4f8:172:10ce::43
gw05s02.gw.freifunk-stuttgart.de. 300 IN AAAA	2001:4ba0:ffff:150::1
gw05s02.gw.freifunk-stuttgart.de. 300 IN A	93.186.197.153
gw07s02.gw.freifunk-stuttgart.de. 300 IN A	163.172.12.135
gw09s02.gw.freifunk-stuttgart.de. 300 IN A	212.227.213.45
gw09s02.gw.freifunk-stuttgart.de. 300 IN AAAA	2001:8d8:1801:35f::92
"""

        lb = GwLoadBalancer()
        # all expected results assume that desiredGwPerSegment == 2
        self.assertEqual(2, lb.desiredGwPerSegment)

    def test_dns_zone_transfer(self):
        lb = GwLoadBalancer()
        lb.dns_zone_transfer()
        self.assertIsNot("", lb.zoneData)

    def test_get_available_gw_from_dns(self):
        lb = GwLoadBalancer()
        lb.zoneData = """gw01n03.gw.freifunk-stuttgart.de. 300 IN A	88.198.230.6
gw01n03.gw.freifunk-stuttgart.de. 300 IN AAAA	2a01:4f8:190:5205:260:2fff:fe08:13cd
"""
        lb.get_available_gw_from_dns()
        self.assertEqual({"gw01n03": {}}, lb.allGws)

    def test_get_ip_from_gw_and_num(self):
        lb = GwLoadBalancer()
        ip = lb.get_ip_from_gw_and_num(1, 3)
        self.assertEqual(ip, "10.191.255.13")

    def test_get_gw_and_num_from_gw(self):
        lb = GwLoadBalancer()
        (gw, num) = lb.get_gw_and_num_from_gw("gw01n03")
        self.assertEqual(gw, 1)
        self.assertEqual(num, 3)

    def test_get_gw_from_gw_and_num(self):
        lb = GwLoadBalancer()
        self.assertEqual(lb.get_gw_from_gw_and_num(1, 3), "gw01n03")

    def test_get_ip_from_gw(self):
        lb = GwLoadBalancer()
        self.assertEqual(lb.getIpFromGw("gw01n03"), "10.191.255.13")

    def test_get_gw_num_from_batctl_line(self):
        lb = GwLoadBalancer()
        line = '  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit'
        (gw, num) = lb.getGwNumFromBatctlLine(line)
        self.assertEqual(gw, 7)
        self.assertEqual(num, 1)

    def test_get_ip_from_batctl_line(self):
        lb = GwLoadBalancer()
        line = '  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit'
        ip = lb.get_ip_from_batctl_line(line)
        self.assertEqual(ip, "10.191.255.71")

    def test_parse_batctl_output(self):
        lb = GwLoadBalancer()
        data = """  02:00:38:01:07:01 (255) 02:00:35:01:07:01 [      bb01]: 64.0/64.0 MBit
  02:00:35:01:04:01 (255) 02:00:35:01:04:01 [      bb01]: 64.0/64.0 MBit
  02:00:35:01:05:03 (255) 02:00:35:01:05:03 [      bb01]: 64.0/64.0 MBit
  02:00:38:01:04:03 (255) 02:00:35:01:04:03 [      bb01]: 64.0/64.0 MBit
  02:00:38:01:09:02 (255) 02:00:35:01:09:02 [      bb01]: 64.0/64.0 MBit"""
        gws = lb.parse_batctl_output(data)
        # expextedGws = ["10.191.255.71","10.191.255.41","10.191.255.53","10.191.255.43","10.191.255.92"]
        expextedGws = ["gw07n01", "gw04n01", "gw05n03", "gw04n03", "gw09n02"]
        self.assertEqual(expextedGws, list(lb.allGws.keys()))

    def test_get_available_gw_from_batctl(self):
        lb = GwLoadBalancer()
        lb.get_available_gw_from_batctl()
        expextedGws = ["gw07n01", "gw04n01", "gw05n03", "gw04n03", "gw09n02"]
        self.assertEqual(expextedGws, list(lb.allGws.keys()))

    def test_add_self_to_gws(self):
        lb = GwLoadBalancer()
        lb.localhost = "gw01n03"
        lb.add_self_to_gws()
        self.assertEqual({"gw01n03": {}}, lb.allGws)

    def test_get_gw_status_url(self):
        lb = GwLoadBalancer()
        url = lb.get_gw_status_url("gw01n03")
        self.assertEqual("http://10.191.255.13/data/gwstatus.json", url)
        lb.use_backbone = False
        url = lb.get_gw_status_url("gw01n03")
        self.assertEqual("http://gw01n03.gw.freifunk-stuttgart.de/data/gwstatus.json", url)

    def test_get_gw_status(self):
        lb = GwLoadBalancer()
        lb.use_backbone = False
        data = lb.get_gw_status("gw01n03")
        self.assertEqual(data["version"], "1")

    def test_validate_gw_status(self):
        lb = GwLoadBalancer()
        lb.zoneData = self.zoneData
        lb.get_ip_to_gw_lookup()

        self.gwstatus["timestamp"] = int(time.time()) - 60 * 60
        status = lb.validate_gw_status("gw01n03", self.gwstatus)
        self.assertFalse(status)

        self.gwstatus["timestamp"] = int(time.time())
        status = lb.validate_gw_status("gw01n03", self.gwstatus)
        self.assertTrue(status)

        self.gwstatus["segments"]["1"]["dnsactive"] = 0
        status = lb.validate_gw_status("gw01n03", self.gwstatus)
        self.assertFalse(status)

        self.gwstatus["segments"]["1"]["dnsactive"] = 1
        self.gwstatus["segments"]["2"]["dnsactive"] = 1
        status = lb.validate_gw_status("gw01n03", self.gwstatus)
        self.assertFalse(status)

        self.gwstatus["segments"]["1"]["dnsactive"] = 1
        self.gwstatus["segments"]["2"]["dnsactive"] = 0
        status = lb.validate_gw_status("gw01n03", self.gwstatus)
        self.assertTrue(status)

    def test_get_all_status(self):
        # this test fetches live data from gw01n03!!!
        lb = GwLoadBalancer()
        lb.use_backbone = False
        gw = "gw01n03"
        lb.allGws = {gw: {}}
        lb.get_all_status()
        self.assertIn("1", lb.allGws[gw]["segments"])
        self.assertIn("2", lb.allGws[gw]["segments"])

    def test_get_status(self):
        lb = GwLoadBalancer()
        gw = "gw01n03"
        lb.zoneData = self.zoneData
        lb.get_ip_to_gw_lookup()
        lb.allGws[gw] = self.gwstatus
        lb.get_status()
        self.assertIn(gw, lb.status["1"])

    def test_get_all_gws_in_segment(self):
        lb = GwLoadBalancer()
        lb.status = self.status
        all = lb.get_all_gws_in_segment(segment="1")
        self.assertEqual(["gw01n03", "gw04n03", "gw05n03", "gw07n01", "gw09n02"], all)
        all = lb.get_all_gws_in_segment(segment="2")
        self.assertEqual(["gw01n03", "gw04n03", "gw05n03", "gw07n01", "gw09n02"], all)

    def test_get_best_gw_for_segment(self):
        lb = GwLoadBalancer()
        lb.status = self.status
        best = lb.get_best_gw_for_segment(segment="1")
        self.assertEqual(["gw07n01", "gw09n02"], best)
        best = lb.get_best_gw_for_segment(segment="2")
        self.assertEqual(["gw07n01", "gw09n02"], best)

    def test_get_gws_with_dnsactive_equal_to(self):
        lb = GwLoadBalancer()
        lb.status = self.status
        active = lb.get_gws_with_dnsactive_equal_to(segment="1", desiredStatus=1)
        self.assertEqual(["gw01n03", "gw05n03", "gw07n01"], active)
        inactive = lb.get_gws_with_dnsactive_equal_to(segment="1", desiredStatus=0)
        self.assertEqual(["gw04n03", "gw09n02"], inactive)

        active = lb.get_gws_with_dnsactive_equal_to(segment="2", desiredStatus=1)
        self.assertEqual(["gw04n03", "gw05n03", "gw07n01", "gw09n02"], active)
        inactive = lb.get_gws_with_dnsactive_equal_to(segment="2", desiredStatus=0)
        self.assertEqual(["gw01n03"], inactive)

        active = lb.get_gws_with_dnsactive_equal_to(segment="2", desiredStatus=1)
        self.assertEqual(["gw04n03", "gw05n03", "gw07n01", "gw09n02"], active)
        inactive = lb.get_gws_with_dnsactive_equal_to(segment="2", desiredStatus=0)
        self.assertEqual(["gw01n03"], inactive)

    def test_get_gws_that_have_to_be_added_to_dns(self):
        lb = GwLoadBalancer()
        lb.status = self.status
        gwsThatHaveToBeAdded = lb.get_gws_that_have_to_be_added_to_dns(segment="1")
        self.assertEqual(["gw09n02"], gwsThatHaveToBeAdded)

        gwsThatHaveToBeAdded = lb.get_gws_that_have_to_be_added_to_dns(segment="2")
        self.assertEqual([], gwsThatHaveToBeAdded)

    def test_get_gws_that_have_to_removed_from_dns(self):
        lb = GwLoadBalancer()
        lb.status = self.status
        gwsThatHaveToBeRemoved = lb.get_gws_that_have_to_removed_from_dns(segment="1")
        self.assertEqual(["gw01n03", "gw05n03"], gwsThatHaveToBeRemoved)

        gwsThatHaveToBeRemoved = lb.get_gws_that_have_to_removed_from_dns(segment="2")
        self.assertEqual(["gw04n03", "gw05n03"], gwsThatHaveToBeRemoved)

    def test_get_result(self):
        lb = GwLoadBalancer()
        lb.localhost = "gw01n03"
        lb.status = self.status
        lb.zoneData = self.zoneData
        lb.target = "gw01n03"
        report = lb.get_result()
        expected = """GWs that have to be added in Segement 1 to dns: gw09n02
GWs that have to be removed in Segement 2 from dns: gw04n03 gw05n03
"""
        self.assertEqual(expected, report)
        expected = [ \
            'update add gw09s01.gw.freifunk-stuttgart.de. 300 A 212.227.213.45', \
            'update add gw09s01.gw.freifunk-stuttgart.de. 300 AAAA 2001:8d8:1801:35f::92', \
            'update delete gw04s02.gw.freifunk-stuttgart.de. 300 A 138.201.55.210', \
            'update delete gw04s02.gw.freifunk-stuttgart.de. 300 AAAA 2a01:4f8:172:10ce::43', \
            'update delete gw05s02.gw.freifunk-stuttgart.de. 300 A 93.186.197.153', \
            'update delete gw05s02.gw.freifunk-stuttgart.de. 300 AAAA 2001:4ba0:ffff:150::1']

        for cmd in expected:
            self.assertIn(cmd, lb.commands_all)
        expected = \
            []
        for cmd in expected:
            self.assertIn(cmd, lb.commands_local)

        lb.target = "gw09n02"
        report = lb.get_result()
        expected = \
            ['update add gw09s01.gw.freifunk-stuttgart.de. 300 A 212.227.213.45', \
             'update add gw09s01.gw.freifunk-stuttgart.de. 300 AAAA 2001:8d8:1801:35f::92']
        for cmd in expected:
            self.assertIn(cmd, lb.commands_local)

    def test_get_ip_to_gw_lookup(self):
        lb = GwLoadBalancer()
        lb.zoneData = self.zoneData
        lb.get_ip_to_gw_lookup()
        expected = \
            {'138.201.55.210': 'gw04n03',
             '163.172.12.135': 'gw07n01',
             '2001:4ba0:ffff:150::1': 'gw05n03',
             '2001:8d8:1801:35f::92': 'gw09n02',
             '212.227.213.45': 'gw09n02',
             '2a01:4f8:172:10ce::43': 'gw04n03',
             '2a01:4f8:190:5205:260:2fff:fe08:13cd': 'gw01n03',
             '88.198.230.6': 'gw01n03',
             '93.186.197.153': 'gw05n03'}
        self.assertEqual(expected, lb.reverseDnsEntries)

    def test_get_active_gw_per_segment_from_dns(self):
        lb = GwLoadBalancer()
        lb.zoneData = self.zoneData
        lb.get_ip_to_gw_lookup()
        active = lb.get_active_gw_per_segment_from_dns(segment="1")
        self.assertEqual(['gw01n03', 'gw05n03', 'gw07n01'], active)
        active = lb.get_active_gw_per_segment_from_dns(segment="2")
        self.assertEqual(['gw04n03', 'gw05n03', 'gw07n01', 'gw09n02'], active)

    def test_validate_status(self):
        lb = GwLoadBalancer()
        lb.zoneData = self.zoneData
        lb.status = self.status
        lb.get_ip_to_gw_lookup()

        result = lb.validate_status()
        self.assertTrue(result)

        temp = lb.status["1"].pop("gw07n01")
        result = lb.validate_status()
        self.assertTrue(result)
        lb.status["1"]["gw07n01"] = temp

        result = lb.validate_status()

    def test_get_record_for_gw(self):
        lb = GwLoadBalancer()
        lb.zoneData = self.zoneData
        gw = "gw01n03"
        ip = lb.get_record_for_gw(gw, "A")
        self.assertEqual("88.198.230.6", ip)

        ip = lb.get_record_for_gw(gw, "AAAA")
        self.assertEqual("2a01:4f8:190:5205:260:2fff:fe08:13cd", ip)

        ip = lb.get_record_for_gw("foobar", "AAAA")
        self.assertIsNone(ip)

    def test_gen_nsupdate(self):
        lb = GwLoadBalancer()
        lb.zoneData = self.zoneData
        lines = lb.gen_nsupdate("gw01n03", "2", "add")
        expected = \
            ['update add gw01s02.gw.freifunk-stuttgart.de. 300 A 88.198.230.6', \
             'update add gw01s02.gw.freifunk-stuttgart.de. 300 AAAA 2a01:4f8:190:5205:260:2fff:fe08:13cd']
        for entry in expected:
            self.assertIn(entry, lines)

    def test_save_result(self):
        lb = GwLoadBalancer()
        lb.commands_local = []
        with tempfile.NamedTemporaryFile() as tf:
            fn = tf.name
        lb.save_result(fn)
        self.assertTrue(os.path.isfile(fn))
        with open(fn) as fp:
            content = fp.read()
        self.assertNotIn("send", content)
        os.remove(fn)

        lb.commands_local = ["line1", "line2"]
        with tempfile.NamedTemporaryFile() as tf:
            fn = tf.name
        lb.save_result(fn)
        self.assertTrue(os.path.isfile(fn))
        with open(fn) as fp:
            content = fp.read().split("\n")
        self.assertEqual(lb.commands_local[0], content[1])
        self.assertEqual(lb.commands_local[1], content[2])
        self.assertEqual("send", content[3])
        os.remove(fn)
