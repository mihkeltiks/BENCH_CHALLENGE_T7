import cmd
import sys
from vllm_test import start_vllm_job, check_vllm_status, stop_vllm_job, benchmark_vllm, remove_vllm_logs

class CLI(cmd.Cmd):
    """
    An interactive command-line interface for managing a VLLM service.
    """
    prompt = 'vllm> '
    intro = "Welcome to the VLLM CLI. Type 'help' for available commands."

    def __init__(self):
        super().__init__()
        self.job_id = None
        self.ip_address = None
        self.vllm_started = False
        self.vllm_ready = False

    def do_start(self, arg):
        """
        Starts the VLLM service using the sbatch script.
        Usage: start vllm
        """
        if arg.lower() == 'vllm':
            if self.job_id:
                self.vllm_started = 1
                print(f"A VLLM job ({self.job_id}) is already being managed.")
                print("Please 'exit' and restart the CLI to manage a new job.")
                return
            
            job_id = start_vllm_job()
            if job_id:
                self.job_id = job_id
                self.vllm_started = 1
        else:
            print("Invalid command. Usage: start vllm")

    def do_check(self, arg):
        """
        Checks the status of the VLLM job and retrieves its IP address.
        Usage: check vllm
        """
        if arg.lower() == 'vllm':
            job_id, ip_address, vllm_ready = check_vllm_status()
            if job_id:
                self.job_id = job_id
            if ip_address:
                self.ip_address = ip_address
                print("-" * 20)
                print(f"State updated: Job ID = {self.job_id}, IP = {self.ip_address}")
                print("-" * 20)
            if vllm_ready:
                self.vllm_ready = True
        else:
            print("Invalid command. Usage: check vllm")

    def do_bench(self, arg):
        """
        Runs a benchmark against the started VLLM server.
        Sends 10 concurrent requests to the completions endpoint.
        Usage: bench vllm
        """
        if arg.lower() == 'vllm':
            if self.ip_address and self.vllm_ready:
                benchmark_vllm(self.ip_address)
            else:
                print("IP address is unknown. Please run 'check vllm' successfully first.")
        else:
            print("Invalid command. Usage: bench vllm")

    def do_clean(self, arg):
        """
        Stops all started servers and deletes the logs.
        """
        if arg.lower() == 'vllm':
            if self.vllm_started:
                if self.job_id:
                    stop_vllm_job(self.job_id)
                remove_vllm_logs()


    def do_exit(self, arg):
        """
        Stops the managed VLLM job and exits the CLI.
        """
        self.do_clean('vllm')
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
