import os
import shutil
import json
import requests
from typing import Optional
import subprocess

from servers import SlurmServer

class LustreServer(SlurmServer):
    def __init__(self):
        super().__init__(
            job_name="lustreIO",
            script_path="../batch_scripts/start_lustre.sh",
            log_dir="logs/lustre/",
            log_out_file="lustre.out",
            log_err_file="lustre.err"
        )
        self.directory = None
        self.bench_task = None

    def set_directory(self, directory: str):
        self.directory = directory
    
    def start_job(self):
        """
        Starts the sbatch script and returns the job ID.
        """
        # Start the sbatch job
        print(f"Starting {self.job_name_prefix} service via sbatch...")
        try:
            cmd = ["sbatch", self.script_path]
            if self.directory:
                cmd.append(self.directory)
            result = subprocess.run(
                cmd,
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

    def _check_readiness(self) -> bool:
        """
        Lustre-specific readiness check.
        For Lustre, being "ready" just means the IP is found.
        """
        if self.ip_address:
            print(f"Lustre Server IP Address: {self.ip_address}")
            return True
        return False

    def benchmark_lustre(self):
        # ToDo Run IO 500 benchmark against the "lustre server"
        script = os.getenv('REPO_SOURCE') + "/batch_scripts/bench_IO500.sh"
        # prompt the user for custom ini file
        ini_file = input("Enter the path to the custom ini file (or press Enter to use default): ").strip()
        if ini_file:
            self.script_path = ini_file
            # Validate the provided ini file path
            if not os.path.isfile(self.script_path):
                print(f"Error: The specified ini file '{self.script_path}' does not exist.")
                return None
            # update ini_file variable in bench_IO500.sh
            try:
                with open("../batch_scripts/bench_IO500.sh", "r") as file:
                    lines = file.readlines()
                with open("../batch_scripts/bench_IO500.sh", "w") as file:
                    for line in lines:
                        if line.startswith("ini_file="):
                            file.write(f'ini_file="{self.script_path}"\n')
                        else:
                            file.write(line)
                print(f"Updated ini_file in bench_IO500.sh to '{self.script_path}'")
            except Exception as e:
                print(f"Error updating bench_IO500.sh: {e}")
                return None
        # prompt the user for number of processes
        num_procs = input("Enter the number of processes to use (or press Enter to use default 16): ").strip()
        nodecount = 1
        if not num_procs.isdigit():
            num_procs = "16"
        else:
            num_procs_int = int(num_procs)
            if num_procs_int > 16:
                nodecount = (num_procs_int + 15) // 16
        # update num_procs variable in bench_IO500.sh
        try:
            with open("../batch_scripts/bench_IO500.sh", "r") as file:
                lines = file.readlines()
            with open("../batch_scripts/bench_IO500.sh", "w") as file:
                for line in lines:
                    if line.startswith("num_procs="):
                        file.write(f'num_procs={num_procs}\n')
                    elif line.startswith("#SBATCH -N"):
                        file.write(f"#SBATCH -N {nodecount}\n")
                    else:
                        file.write(line)
            print(f"Updated num_procs in bench_IO500.sh to '{num_procs}'")
        except Exception as e:
            print(f"Error updating bench_IO500.sh: {e}")
            return None
        # start the benchmark
        print("Starting IO500 benchmark...")
        # print("This may take a while...")
        # result = subprocess.run(["srun","-n 4","../utils/io500/io500", "io500.ini"], check=True, capture_output=True, text=True)
        # print("IO500 benchmark completed.")
        # with open("logs/IO500/output.log", "w") as log_file:
        #     self.bench_task = subprocess.Popen(
        #         ["srun", "-n", "4", "../utils/io500/io500", "io500.ini"],
        #         stdout=log_file,
        #         stderr=log_file,
        #         preexec_fn=os.setpgrp
        #     )
        run = subprocess.run(
            ["sbatch", script],
            capture_output=True,
            text=True,
            check=True
        )
        self.bench_task = run.stdout.strip().split()[-1]
        # self.bench_task = subprocess.Popen(["srun","-n 4","../utils/io500/io500", "io500.ini"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"IO500 benchmark started with PID: {self.bench_task}")
        print("The result is stored in the directory: ./logs/IO500/IO500.out")
        print("You can monitor job completion by \"check lustre\" command.")
        return

    def display_logs(self):
        """
        Prompt user whether to display log file for current job
        or to display IO500 benchmark results (if previous runs exist)
        """
        base_dir = "logs/IO500"

        def tail(path, lines=200):
            try:
                with open(path, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    end = f.tell()
                    size = 1024
                    data = b""
                    while end > 0 and len(data.splitlines()) <= lines:
                        start = max(0, end - size)
                        f.seek(start)
                        chunk = f.read(end - start)
                        data = chunk + data
                        end = start
                        size *= 2
                    text = data.decode(errors="replace")
                    return "\n".join(text.splitlines()[-lines:])
            except Exception as e:
                return f"Error reading file {path}: {e}"

        if os.path.exists(base_dir):
            prev_runs  = [e for e in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, e))]
            root_files = [f for f in ("IO500.out", "IO500.err") if os.path.exists(os.path.join(base_dir, f))]
            if prev_runs:
                choice = input("Previous IO500 run results found. View previous runs? (y/n): ").strip().lower()
                if choice == "y" or choice == "yes":
                    # display choice enumeration of previous runs
                    for i, d in enumerate(prev_runs, 1):
                        print(f"{i}. {d}")
                    while True:
                        sel = input("Select a run number to view (or press Enter to cancel): ").strip()
                        if not sel.isdigit():
                            break
                        sel_idx = int(sel) - 1
                        if sel_idx < 0 or sel_idx >= len(prev_runs):
                            print("Invalid selection.")
                            continue
                        chosen_run = prev_runs[sel_idx]
                        choice = input("Display full result.txt (f) or summary (s)?").strip().lower()
                        out_path = os.path.join(base_dir, chosen_run, "result.txt" if choice == "f" else "result_summary.txt")
                        if os.path.exists(out_path):
                            try:
                                with open(out_path, "r", errors="replace") as f:
                                    print(f.read())
                            except Exception as e:
                                print(f"Error reading {out_path}: {e}")
                        else:
                            print(f"Something has gone wrong, no result file found at {out_path}.")
            if root_files:
                choice = input("Current IO500 job output files found. View them? (y/n): ").strip().lower()
                if choice == "y" or choice == "yes":
                    for f in root_files:
                        path = os.path.join(base_dir, f)
                        print(f"--- Contents of {f} ---")
                        print(tail(path, lines=200))
        
        super().display_logs()

    def _check_readiness(self):
        if self.bench_task is not None:
            job_running = subprocess.run(
                ["squeue", "-j", str(self.bench_task)],
                capture_output=True,
                text=True
            )
            if "RUNNING" in job_running.stdout:
                print(f"IO500 benchmark is still RUNNING with JOBID: {self.bench_task}")
                return False
            if "PENDING" in job_running.stdout:
                print(f"IO500 benchmark is still PENDING with JOBID: {self.bench_task}")
                return False
            if job_running.returncode != 0 or self.bench_task not in job_running.stdout:
                print(f"IO500 benchmark has COMPLETED. Result:")
                try:
                    with open("logs/IO500/IO500.out", "r") as result_file:
                        print(result_file.read())
                except FileNotFoundError:
                    print("Result file not found.")
                self.bench_task = None
        return True

    def stop_job(self):
        """
        Stops the running SLURM job using scancel.
        Destroys the specified directory if provided, default dir otherwise
        """
        if not self.job_id:
            print(f"No {self.job_name_prefix} job ID provided to stop.")
            return
        
        print(f"Stopping {self.job_name_prefix} job ID: {self.job_id}")
        try:
            if self.bench_task is not None:
                print(f"Cancelling benchmark job ID: {self.bench_task}")
                subprocess.run(["scancel", str(self.bench_task)], check=True, capture_output=True)
                self.bench_task = None
            subprocess.run(["scancel", self.job_id], check=True, capture_output=True)
            print(f"Job {self.job_id} cancelled successfully.")
            self.running = 0
            self.job_id = None
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error stopping job {self.job_id}: {e}")
        # Clean up the Lustre directory
        if self.directory and os.path.exists(self.directory):
            print(f"Removing Lustre directory: {self.directory}")
            try:
                shutil.rmtree(self.directory)
                print(f"Lustre directory {self.directory} removed successfully.")
            except Exception as e:
                print(f"Error removing Lustre directory {self.directory}: {e}")
        else:
            print("Removing default Lustre test directory")
            dir = os.getenv('PROJECT') + "/utils/lustre_test_dir"
            if os.path.exists(dir):
                try:
                    shutil.rmtree(dir)
                    print(f"Default Lustre test directory {dir} removed successfully.")
                except Exception as e:
                    print(f"Error removing default Lustre test directory {dir}: {e}")
        
        symlink = os.getenv('REPO_SOURCE') + "/utils/lustre_test_dir"
        if os.path.exists(symlink):
            print(f"Removing symlink: {symlink}")
            try:
                os.remove(symlink)
                print(f"Symlink {symlink} removed successfully.")
            except Exception as e:
                print(f"Error removing symlink {symlink}: {e}")