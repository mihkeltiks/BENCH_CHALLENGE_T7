import cmd
import sys
from vllm_test import VLLMManager
from grafana import GrafanaManager

class CLI(cmd.Cmd):
    """
    An interactive command-line interface for benchmarking HPC services.
    """
    prompt = 'bench> '
    intro = "Welcome to the BENCH CLI. Type 'help' for available commands."

    def __init__(self):
        super().__init__()
        self.vllm_manager = VLLMManager()
        self.grafana_manager = GrafanaManager()

    def do_start(self, arg):
        """
        Starts the service using the sbatch script.
        Usage: start [vllm|grafana|prometheus]
        """
        if arg.lower() == 'vllm':
            if self.vllm_manager.running:
                print(f"A VLLM job ({self.vllm_manager.job_id}) is already being managed.")
                print("Please 'exit' and restart the CLI or `clean vllm` to manage a new job.")
                return
            job_id = self.vllm_manager.start_vllm_job()
            if job_id:
                self.vllm_manager.job_id = job_id
                self.vllm_manager.running = 1
        elif arg.lower() == 'prometheus':
            print("Prometheus integration is not implemented yet.")
        elif arg.lower() == 'grafana':
            if self.grafana_manager.running:
                print(f"A Grafana job ({self.grafana_manager.job_id}) is already being managed.")
                print("Please 'exit' and restart the CLI or `clean grafana` to manage a new job.")
                return
            job_id = self.grafana_manager.start_grafana()
            if job_id:
                self.grafana_manager.job_id = job_id
                self.grafana_manager.running = 1
        else:
            print("Invalid command. Usage: start vllm")

    def do_check(self, arg):
        """
        Checks the status of the job and retrieves its IP address.
        Usage: check [vllm|grafana|prometheus]
        """
        if arg.lower() == 'vllm':
            job_id, ip_address, vllm_ready = self.vllm_manager.check_vllm_status()
            if job_id:
                self.vllm_manager.job_id = job_id
            if ip_address:
                self.vllm_manager.ip_address = ip_address
                self.vllm_manager.running = 1
                print("-" * 20)
                print(f"State updated: Job ID = {self.vllm_manager.job_id}, IP = {self.vllm_manager.ip_address}")
                print("-" * 20)
            if vllm_ready:
                self.vllm_manager.vllm_ready = True
        elif arg.lower() == 'grafana':
            job_id, ip_address, grafana_ready = self.grafana_manager.check_grafana_status()
            if job_id:
                self.grafana_manager.job_id = job_id
            if ip_address:
                self.grafana_manager.ip_address = ip_address
                self.grafana_manager.running = 1
                print("-" * 20)
                print(f"State updated: Job ID = {self.grafana_manager.job_id}, IP = {self.grafana_manager.ip_address}")
                print("-" * 20)
            if grafana_ready:
                self.grafana_manager.grafana_ready = True
        else:
            print("Invalid command. Usage: check vllm")

    def do_bench(self, arg):
        """
        Runs a benchmark against the started VLLM server.
        Sends 10 concurrent requests to the completions endpoint.
        Usage: bench vllm
        """
        if arg.lower() == 'vllm':
            if self.vllm_manager.ip_address and self.vllm_manager.vllm_ready:
                self.vllm_manager.benchmark_vllm()
            else:
                print("IP address is unknown. Please run 'check vllm' successfully first.")
        else:
            print("Invalid command. Usage: bench vllm")

    def do_clean(self):
        """
        Stops all started servers and deletes the logs.
        """
        if self.vllm_manager.running:
            if self.vllm_manager.job_id:
                self.vllm_manager.stop_vllm_job(self.vllm_manager.job_id)
            self.vllm_manager.remove_vllm_logs()
    
        if self.grafana_manager.running:
            if self.grafana_manager.job_id:
                self.grafana_manager.stop_grafana_job(self.grafana_manager.job_id)
            self.grafana_manager.remove_grafana_logs()


    def do_exit(self, arg):
        """
        Stops the managed VLLM job and exits the CLI.
        """
        self.do_clean()
        
        print("Exiting CLI...")
        print("Goodbye!")
        return True

    def do_EOF(self, arg):
        """
        Exits the CLI on EOF (Ctrl-D).
        """
        print()
        return self.do_exit(arg)

if __name__ == '__main__':
    CLI().cmdloop()
