from prometheus_client import Gauge, start_http_server
# from lustre import Lustre
import subprocess
import argparse
import time
import os
import socket
import psutil
from mpi4py import MPI

parser = argparse.ArgumentParser(description='Hardware Metric Collector')
parser.add_argument('--service-name', type=str, required=True, help='Name of the service to monitor')
parser.add_argument('--interval', type=int, default=1, help='Scrape interval in seconds')

def get_cpu_load():
	# Returns 1, 5, 15 min load average
	return os.getloadavg()

def get_memory_usage():
	mem = psutil.virtual_memory()
	return mem.total, mem.used, mem.available, mem.percent

def main():

	args = parser.parse_args()
	hostname = socket.gethostname()
	job_title = args.service_name
	job_id = os.environ.get('SLURM_JOB_ID', 'unknown')

	comm = MPI.COMM_WORLD
	rank = comm.Get_rank()
	size = comm.Get_size()

	# Each process collects its own metrics
	while True:
		load1, load5, load15 = get_cpu_load()
		total, used, available, percent = get_memory_usage()
		local_metrics = {
			'hostname': hostname,
			'job_title': job_title,
			'job_id': job_id,
			'cpu_load_1m': load1,
			'cpu_load_5m': load5,
			'cpu_load_15m': load15,
			'mem_total': total,
			'mem_used': used,
			'mem_available': available,
			'mem_percent': percent
		}

		# Gather all metrics at rank 0
		all_metrics = comm.gather(local_metrics, root=0)

		if rank == 0:
			# Only master publishes to Prometheus
			# Setup Gauges once
			if not hasattr(main, "gauges"):
				main.gauges = {
					'cpu_load_1m': Gauge('cpu_load_1m', 'CPU load average (1m)', ['hostname', 'job_title', 'job_id']),
					'cpu_load_5m': Gauge('cpu_load_5m', 'CPU load average (5m)', ['hostname', 'job_title', 'job_id']),
					'cpu_load_15m': Gauge('cpu_load_15m', 'CPU load average (15m)', ['hostname', 'job_title', 'job_id']),
					'mem_total': Gauge('system_memory_total_bytes', 'Total system memory', ['hostname', 'job_title', 'job_id']),
					'mem_used': Gauge('system_memory_used_bytes', 'Used system memory', ['hostname', 'job_title', 'job_id']),
					'mem_available': Gauge('system_memory_available_bytes', 'Available system memory', ['hostname', 'job_title', 'job_id']),
					'mem_percent': Gauge('system_memory_percent', 'System memory usage percent', ['hostname', 'job_title', 'job_id'])
				}
				start_http_server(8010)

			for metrics in all_metrics:
				for key in ['cpu_load_1m', 'cpu_load_5m', 'cpu_load_15m', 'mem_total', 'mem_used', 'mem_available', 'mem_percent']:
					main.gauges[key].labels(hostname=metrics['hostname'], job_title=metrics['job_title'], job_id=metrics['job_id']).set(metrics[key])
		time.sleep(args.interval)

if __name__ == "__main__":
	main()


