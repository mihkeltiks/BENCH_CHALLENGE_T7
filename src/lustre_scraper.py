from prometheus_client import Gauge, start_http_server
from lustre import Lustre
import subprocess
import argparse

parser = argparse.ArgumentParser(description='Lustre Scraper')
parser.add_argument('--lustre-dir', type=str, required=True, help='Lustre directory to monitor')
args = parser.parse_args()

# parse cmd line args for --lustre-dir
lustre_dir = args.lustre_dir


# Theoretically this script scrapes lustre metrics and exposes them via prometheus client
# for now it remains ToDo
#
# Current problem: don't know how to get lfs and lctl to play nice and fetch me the metrics
# Since there is no iostat available on meluxina, I have no good idea on how to scrape metrics

print(f"Starting Lustre scraper for directory: {lustre_dir}")


print("Starting Prometheus HTTP server on port 8000")
start_http_server(8000)
