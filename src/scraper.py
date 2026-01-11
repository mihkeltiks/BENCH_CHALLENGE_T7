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

def get_gpu_metrics():
	"""
	Collect basic GPU metrics using nvidia-smi.
	Returns a list of dicts with keys: index, util, mem_total_bytes, mem_used_bytes, temp_c.
	If nvidia-smi is unavailable or no GPUs are present, returns an empty list.
	"""
	try:
		result = subprocess.run(
			[
				"nvidia-smi",
				"--query-gpu=index,utilization.gpu,memory.total,memory.used,temperature.gpu",
				"--format=csv,noheader,nounits",
			],
			capture_output=True,
			text=True,
			check=False,
			timeout=5,
		)
		if result.returncode != 0 or not result.stdout.strip():
			return []
		metrics = []
		for line in result.stdout.strip().splitlines():
			parts = [p.strip() for p in line.split(",")]
			if len(parts) != 5:
				continue
			try:
				idx = int(parts[0])
				util = float(parts[1])
				mem_total = float(parts[2]) * 1024 * 1024  # MiB -> bytes
				mem_used = float(parts[3]) * 1024 * 1024  # MiB -> bytes
				temp = float(parts[4])
				metrics.append(
					{
						"index": idx,
						"util": util,
						"mem_total_bytes": mem_total,
						"mem_used_bytes": mem_used,
						"temp_c": temp,
					}
				)
			except ValueError:
				continue
		return metrics
	except FileNotFoundError:
		# nvidia-smi not present
		return []
	except Exception:
		return []

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
					'mem_percent': Gauge('system_memory_percent', 'System memory usage percent', ['hostname', 'job_title', 'job_id']),
					'gpu_util_percent': Gauge('gpu_utilization_percent', 'GPU utilization percent', ['hostname', 'job_title', 'job_id', 'gpu_index']),
					'gpu_mem_total': Gauge('gpu_memory_total_bytes', 'GPU memory total bytes', ['hostname', 'job_title', 'job_id', 'gpu_index']),
					'gpu_mem_used': Gauge('gpu_memory_used_bytes', 'GPU memory used bytes', ['hostname', 'job_title', 'job_id', 'gpu_index']),
					'gpu_temp_c': Gauge('gpu_temperature_celsius', 'GPU temperature Celsius', ['hostname', 'job_title', 'job_id', 'gpu_index'])
				}
				start_http_server(8010)

			for metrics in all_metrics:
				for key in ['cpu_load_1m', 'cpu_load_5m', 'cpu_load_15m', 'mem_total', 'mem_used', 'mem_available', 'mem_percent']:
					main.gauges[key].labels(hostname=metrics['hostname'], job_title=metrics['job_title'], job_id=metrics['job_id']).set(metrics[key])
			
			# GPU metrics (polled on rank 0)
			for gpu in get_gpu_metrics():
				lbls = dict(hostname=hostname, job_title=job_title, job_id=job_id, gpu_index=str(gpu['index']))
				main.gauges['gpu_util_percent'].labels(**lbls).set(gpu['util'])
				main.gauges['gpu_mem_total'].labels(**lbls).set(gpu['mem_total_bytes'])
				main.gauges['gpu_mem_used'].labels(**lbls).set(gpu['mem_used_bytes'])
				main.gauges['gpu_temp_c'].labels(**lbls).set(gpu['temp_c'])
		time.sleep(args.interval)

if __name__ == "__main__":
	main()


