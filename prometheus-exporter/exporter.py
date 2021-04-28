import prometheus_client as prometheus
import argparse
import requests
from urllib.parse import urlparse
import logging
import time
import sys
import json

def read_gwstatus_urls(gwstatus_url_file):
    urls = {}
    for line in gwstatus_url_file:
        if (not line.startswith("#") and line.strip()):
            parsed_line = line.split("|", 1)
            gw_name = parsed_line[0].strip()
            url = parsed_line[1].strip()
            urls[gw_name] = url
    return urls

def download_gw_status(gwstatus_urls):
    status_dict = {}
    for gw_name, url in gwstatus_urls.items():
        if gw_name in status_dict:
            logging.warning("Duplicate gwname %s - ignoring!", gw_name)
            continue

        logging.debug("Fetching %s status data from '%s'", gw_name, url)
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            status_dict[gw_name] = resp.json()
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            logging.error("Error fetching status data from %s: '%s'", url, e)
    return status_dict

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("gwstatus_url_file", type=argparse.FileType("r"), help="File with one URL to gwstatus.json per line")
    ap.add_argument("--port", help="Listen Port", default=8000, type=int)
    ap.add_argument("--addr", help="Listen Address, default all", default="")
    ap.add_argument("--update-interval", help="Update data every N seconds", default=300, type=int)
    ap.add_argument("--loglevel", help="Set the desired level of logging", default="warning", choices=["debug", "warning", "error"])
    args = ap.parse_args()
    
    if args.loglevel == "debug":
        logging.basicConfig(level=logging.DEBUG)
    elif args.loglevel == "warning":
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.ERROR)

    gwstatus_urls = read_gwstatus_urls(args.gwstatus_url_file)

    prometheus_registry = prometheus.CollectorRegistry()
    preference_gauge = prometheus.Gauge(
            "gw_loadbalancing_pref",
            "Current Preference. Range -inf to 100, where 100 is most willing to accept more nodes.",
            ['gateway', 'segment'],
            registry=prometheus_registry
    )
    prometheus.start_http_server(args.port, args.addr, prometheus_registry)

    while True:
        # first download status files to avoid blocking to long after clearing gauge
        status_jsons = download_gw_status(gwstatus_urls)

        preference_gauge.clear()
        for gw_name, status_json in status_jsons.items():
            try:
                for segment_number, segment_status in status_json["segments"].items():
                    preference_gauge.labels(gateway=gw_name, segment=segment_number).set(segment_status["preference"])
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                logging.error("Error exporting preference for %s: %s", gw_name, e)
        time.sleep(args.update_interval)


