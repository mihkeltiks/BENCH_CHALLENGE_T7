from prometheus_client import Gauge, start_http_server
# from lustre import Lustre
import subprocess
import argparse
import time
import psutil

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

class LustreScraper:
    def __init__(self, lustre_dir):
        # self.lustre = Lustre(lustre_dir)

        # Define Prometheus Gauges for various Lustre metrics
        self.read_bytes_gauge = Gauge('lustre_read_bytes', 'Total read bytes from Lustre')
        self.write_bytes_gauge = Gauge('lustre_write_bytes', 'Total write bytes to Lustre')
        self.read_ops_gauge = Gauge('lustre_read_ops', 'Total read operations on Lustre')
        self.write_ops_gauge = Gauge('lustre_write_ops', 'Total write operations on Lustre')

    def scrape_metrics(self):
        pass

print("Starting Prometheus HTTP server on port 8000")
start_http_server(8000)

scraper = LustreScraper(lustre_dir)

sleeping_time = 10  # seconds
while True:
    scraper.scrape_metrics()
    time.sleep(sleeping_time)
