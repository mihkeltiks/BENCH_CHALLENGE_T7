import subprocess
import os
import time

class GrafanaManager:
    def __init__(self):
        self.job_id = None
        self.ip_address = None
        self.running = 0
        self.grafana_ready = False
        self.GRAFANA_SCRIPT_PATH = "../examples/monitoring/start_grafana.sh"
        self.GRAFANA_LOGS_PATH = "logs/grafana/"

    def start_grafana(self):
        """
        Starts the Grafana sbatch script and returns the job ID.

        Returns:
            str: The submitted job ID, or None if submission fails.
        """
        print("Starting Grafana service via sbatch...")
        try:
            result = subprocess.run(
                ["sbatch", self.GRAFANA_SCRIPT_PATH],
                capture_output=True,
                text=True,
                check=True
            )
            job_id = result.stdout.strip().split()[-1]
            print(f"Grafana script submitted successfully. Job ID: {job_id}")
            self.job_id = job_id
            return job_id
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError) as e:
            print(f"Error starting Grafana job: {e}")
            print("Please ensure 'sbatch' is in your PATH and the script exists.")
            return None

    def check_grafana_status(self):
        """
        Checks for a running Grafana job and retrieves its IP address from the logs.

        Returns:
            tuple: A tuple containing the job ID (str) and IP address (str),
                or (None, None) if not found or not ready.
        """
        print("Checking Grafana job status...")
        job_id = None
        ip_address = None
        user = os.getenv("USER")

        try:
            squeue_command = ["squeue", "-h", "-o", "%i %j", "-u", user]
            result = subprocess.run(squeue_command, capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1].startswith("grafana"):
                    job_id = parts[0]
                    print(f"Active Grafana job found with ID: {job_id}.")
                    break
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error checking squeue: {e}")
            return None, None, False

        if not job_id:
            print("No active Grafana job found with a name starting with 'vllm'.")
            return None, None, False

        log_file = os.path.join(self.GRAFANA_LOGS_PATH, "grafana.out")
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
                        print(f"SSH TUNNEL (Execute on your local machine): ssh -p 8822 {os.getenv('USER')}@login.lxp.lu -NL 3000:{ip_address}:3000")
                        break
                except (IndexError):
                    pass
            
            print(f"IP not found yet. Retrying in 3 seconds... (Attempt {i+1}/5)")
            time.sleep(3)
        
        if not ip_address:
            print("Could not find IP address in the log file after several attempts.")
            return job_id, None, False

        return job_id, ip_address, False


    def stop_grafana_job(self, job_id):
        """
        Stops a running SLURM job using scancel.

        Args:
            job_id (str): The ID of the job to cancel.
        """
        if not job_id:
            print("No job ID provided to stop.")
            return
        
        print(f"Stopping Grafana job ID: {job_id}")
        try:
            subprocess.run(["scancel", job_id], check=True)
            print(f"Job {job_id} cancelled successfully.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error stopping job {job_id}: {e}")

    def remove_grafana_logs(self):
        if os.path.exists(self.GRAFANA_LOGS_PATH + 'grafana.out'):
            os.remove(self.GRAFANA_LOGS_PATH + 'grafana.out')
        if os.path.exists(self.GRAFANA_LOGS_PATH + 'grafana.err'):
            os.remove(self.GRAFANA_LOGS_PATH + 'grafana.err')
