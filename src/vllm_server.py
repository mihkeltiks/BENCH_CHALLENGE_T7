import subprocess
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from servers import SlurmServer

class VLLMServer(SlurmServer):
    def __init__(self):
        super().__init__(
            job_name="vllm",
            script_path="../batch_scripts/start_vllm.sh",
            log_dir="logs/vllm/",
            log_out_file="vllm.out",
            log_err_file="vllm.err"
        )

    def _check_readiness(self):
        """
        VLLM-specific readiness check.
        Polls the log file for the 'server is ready' message.
        """
        print(f"Checking if VLLM server is ready, this can take a while.")
        for i in range(5):
            if os.path.exists(self.log_out_file):
                try:
                    grep_command = ["grep", 'Starting vLLM API server 0', self.log_out_file]
                    grep_result = subprocess.run(grep_command, capture_output=True, text=True, check=False)
                    if grep_result.returncode == 0 and grep_result.stdout:
                        print(f"vLLM server is ready to take requests")
                        return True
                except (IndexError):
                    pass
            
            print(f"Server not ready yet, retrying in 10 seconds... (Attempt {i+1}/5)")
            time.sleep(10)
        
        print("VLLM server did not become ready.")
        return False

    def benchmark_vllm(self, port=8000, num_requests=10):
        """
        (This method is specific to VLLM and remains unchanged)
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

        def send_request(req_id):
            try:
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