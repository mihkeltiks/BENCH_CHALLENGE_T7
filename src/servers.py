# servers.py

import subprocess
import os
import time
from abc import ABC, abstractmethod

class SlurmServer(ABC):
    """
    An abstract base class for managing a server application submitted as a SLURM job.
    
    It handles common logic for starting, stopping, and checking the status of a job.
    """
    def __init__(self, job_name, script_path, log_dir, log_out_file, log_err_file):
        self.job_id = None
        self.ip_address = None
        self.running = 0
        self.ready = False # Generic readiness flag
        
        # Configuration for the specific server
        self.job_name_prefix = job_name
        self.script_path = script_path
        self.log_dir = log_dir
        self.log_out_file = os.path.join(self.log_dir, log_out_file)
        self.log_err_file = os.path.join(self.log_dir, log_err_file)
        self.user = os.getenv("USER")

    def start_job(self):
        """
        Starts the sbatch script and returns the job ID.
        """
        print(f"Starting {self.job_name_prefix} service via sbatch...")
        try:
            result = subprocess.run(
                ["sbatch", self.script_path],
                capture_output=True,
                text=True,
                check=True
            )
            self.job_id = result.stdout.strip().split()[-1]
            print(f"{self.job_name_prefix} script submitted. Job ID: {self.job_id}")
            return self.job_id
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError) as e:
            print(f"Error starting {self.job_name_prefix} job: {e}")
            return None

    def stop_job(self):
        """
        Stops the running SLURM job using scancel.
        """
        if not self.job_id:
            print(f"No {self.job_name_prefix} job ID provided to stop.")
            return
        
        print(f"Stopping {self.job_name_prefix} job ID: {self.job_id}")
        try:
            subprocess.run(["scancel", self.job_id], check=True, capture_output=True)
            print(f"Job {self.job_id} cancelled successfully.")
            self.running = 0
            self.job_id = None
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error stopping job {self.job_id}: {e}")

    def remove_logs(self):
        """
        Removes the .out and .err log files for this job.
        """
        print(f"Removing {self.job_name_prefix} logs...")
        if os.path.exists(self.log_out_file):
            os.remove(self.log_out_file)
        if os.path.exists(self.log_err_file):
            os.remove(self.log_err_file)

    def _find_job_id(self):
        """Helper to find the active job ID using squeue."""
        print(f"Checking {self.job_name_prefix} job status via squeue...")
        try:
            squeue_command = ["squeue", "-h", "-o", "%i %j", "-u", self.user]
            result = subprocess.run(squeue_command, capture_output=True, text=True, check=True)
            
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1].startswith(self.job_name_prefix):
                    job_id = parts[0]
                    print(f"Active {self.job_name_prefix} job found with ID: {job_id}.")
                    return job_id
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error checking squeue: {e}")
        
        print(f"No active job found with name starting with '{self.job_name_prefix}'.")
        return None

    def _find_ip_address(self):
        """Helper to poll the log file for the IP address."""
        print(f"Polling log file for IP address: {self.log_out_file}")
        for i in range(5):
            if os.path.exists(self.log_out_file):
                try:
                    grep_command = ["grep", 'IP ADDRESS:', self.log_out_file]
                    grep_result = subprocess.run(grep_command, capture_output=True, text=True, check=False)
                    
                    if grep_result.returncode == 0 and grep_result.stdout:
                        ip_line = grep_result.stdout.strip().splitlines()[-1]
                        ip_address = ip_line.split("IP ADDRESS: ")[1]
                        print(f"Success! IP Address found: {ip_address}")
                        return ip_address
                except IndexError:
                    pass  # Ignore lines that don't split correctly
            
            print(f"IP not found yet. Retrying in 3 seconds... (Attempt {i+1}/5)")
            time.sleep(3)
        
        print("Could not find IP address in the log file after several attempts.")
        return None

    @abstractmethod
    def _check_readiness(self):
        """
        Abstract method for service-specific readiness checks.
        This is called *after* an IP address has been found.
        Must be implemented by the child class.
        Should return True if ready, False otherwise.
        """
        pass

    def check_status(self):
        """
        Checks job status, finds IP, and runs readiness checks.
        This method updates the object's internal state.
        
        Returns:
            tuple: (job_id, ip_address, ready)
        """
        # 1. Find the job ID
        job_id = self._find_job_id()
        if not job_id:
            return None, None, False
        self.job_id = job_id
        
        # 2. Find the IP Address
        ip_address = self._find_ip_address()
        if not ip_address:
            return self.job_id, None, False
        self.ip_address = ip_address
        self.running = 1 # Mark as running now that we have an IP
        
        # 3. Run the service-specific readiness check
        self.ready = self._check_readiness()
        
        return self.job_id, self.ip_address, self.ready