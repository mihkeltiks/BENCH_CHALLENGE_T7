import subprocess
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed



class VLLMManager:
    def __init__(self):
        self.job_id = None
        self.ip_address = None
        self.running = 0
        self.vllm_ready = False
        self.VLLM_SCRIPT_PATH = "../examples/vllm/start_server.sh"
        self.VLLM_LOGS_PATH = "logs/vllm/"

    def start_vllm_job(self):
        """
        Starts the VLLM sbatch script and returns the job ID.

        Returns:
            str: The submitted job ID, or None if submission fails.
        """
        print("Starting VLLM service via sbatch...")
        try:
            result = subprocess.run(
                ["sbatch", self.VLLM_SCRIPT_PATH],
                capture_output=True,
                text=True,
                check=True
            )
            job_id = result.stdout.strip().split()[-1]
            print(f"VLLM script submitted successfully. Job ID: {job_id}")
            self.job_id = job_id
            return job_id
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError) as e:
            print(f"Error starting VLLM job: {e}")
            print("Please ensure 'sbatch' is in your PATH and the script exists.")
            return None

    def check_vllm_status(self):
        """
        Checks for a running VLLM job and retrieves its IP address from the logs.

        Returns:
            tuple: A tuple containing the job ID (str) and IP address (str),
                or (None, None) if not found or not ready.
        """
        print("Checking VLLM job status...")
        job_id = None
        ip_address = None
        user = os.getenv("USER")

        try:
            squeue_command = ["squeue", "-h", "-o", "%i %j", "-u", user]
            result = subprocess.run(squeue_command, capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1].startswith("vllm"):
                    job_id = parts[0]
                    print(f"Active VLLM job found with ID: {job_id}.")
                    break
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error checking squeue: {e}")
            return None, None, False

        if not job_id:
            print("No active VLLM job found with a name starting with 'vllm'.")
            return None, None, False

        log_file = os.path.join(self.VLLM_LOGS_PATH, "vllm.out")
        print(f"Polling log file for IP address: {log_file}")

        for i in range(5):
            if os.path.exists(log_file):
                try:
                    grep_command = ["grep", 'IP ADDRESS:', log_file]
                    grep_result = subprocess.run(grep_command, capture_output=True, text=True, check=False)
                    if grep_result.returncode == 0 and grep_result.stdout:
                        ip_line = grep_result.stdout.strip().splitlines()[-1]
                        ip_address = ip_line.split("IP ADDRESS: ")[1]
                        print(f"Success! IP Address found: {ip_address}")
                        break
                except (IndexError):
                    pass
            
            print(f"IP not found yet. Retrying in 3 seconds... (Attempt {i+1}/5)")
            time.sleep(3)
        
        if not ip_address:
            print("Could not find IP address in the log file after several attempts.")
            return job_id, None, False

        print(f"Checking if server is ready, this can take a while.")
        for i in range(5):
            if os.path.exists(log_file):
                try:
                    grep_command = ["grep", 'Starting vLLM API server 0', log_file]
                    grep_result = subprocess.run(grep_command, capture_output=True, text=True, check=False)
                    if grep_result.returncode == 0 and grep_result.stdout:
                        print(f"vLLM server is ready to take requests")
                        return job_id, ip_address, True
                except (IndexError):
                    pass
            
            print(f"Server not ready yet, retrying in 10 seconds... (Attempt {i+1}/5)")
            time.sleep(10)
        return job_id, ip_address, False


    def stop_vllm_job(self, job_id):
        """
        Stops a running SLURM job using scancel.

        Args:
            job_id (str): The ID of the job to cancel.
        """
        if not job_id:
            print("No job ID provided to stop.")
            return
        
        print(f"Stopping VLLM job ID: {job_id}")
        try:
            subprocess.run(["scancel", job_id], check=True)
            print(f"Job {job_id} cancelled successfully.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error stopping job {job_id}: {e}")

    def remove_vllm_logs(self):
        if os.path.exists(self.VLLM_LOGS_PATH + 'vllm.out'):
            os.remove(self.VLLM_LOGS_PATH + 'vllm.out')
        if os.path.exists(self.VLLM_LOGS_PATH + 'vllm.err'):
            os.remove(self.VLLM_LOGS_PATH + 'vllm.err')

    def benchmark_vllm(self, port=8000, num_requests=10):
        """
        Sends multiple concurrent requests to the VLLM server to test performance.

        Args:
            ip_address (str): The IP address of the VLLM server.
            port (int): The port the server is listening on.
            num_requests (int): The number of concurrent requests to send.
        """
        if not self.ip_address:
            print("Cannot run benchmark without an IP address.")
            return

        url = f"http://{self.ip_address}:{port}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "model": "google/gemma-3-27b-it",
            "messages": [
                {"role": "user", "content": "What is the capital of France?"}
            ],
            "max_tokens": 50
        }
        print(url)
        print(f"Starting benchmark with {num_requests} requests to {url}...")

        def send_request(self, req_id):
            try:
                # Set a timeout for the request
                response = requests.post(url, headers=headers, json=payload, timeout=90)
                if response.status_code == 200:
                    print(f"Request {req_id}: Success (Status {response.status_code})")
                    return True
                else:
                    print(f"Request {req_id}: Failed (Status {response.status_code}) - {response.text[:100]}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"Request {req_id}: Error - {e}")
                return False

        success_count = 0
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(send_request, i + 1) for i in range(num_requests)]
            for future in as_completed(futures):
                if future.result():
                    success_count += 1
        
        print("-" * 30)
        print(f"Benchmark Complete: {success_count} / {num_requests} requests were successful.")
        print("-" * 30)

