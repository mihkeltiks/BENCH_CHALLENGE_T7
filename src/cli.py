import cmd
import sys
from vllm_server import VLLMServer
from monitor_server import MonitorServer
from chroma_server import ChromaServer

class CLI(cmd.Cmd):
    """
    An interactive command-line interface for benchmarking HPC services.
    """
    prompt = 'bench> '
    intro = "Welcome to the BENCH CLI. Type 'help' for available commands."

    def __init__(self):
        super().__init__()
        self.vllm_server = VLLMServer()
        self.monitor_server = MonitorServer()
        self.chroma_server = ChromaServer()

    def do_start(self, arg):
        """
        Starts the service using the sbatch script.
        Usage: start [vllm|monitors|chroma]
        """
        if arg.lower() == 'vllm':
            if self.vllm_server.running:
                print(f"A VLLM job ({self.vllm_server.job_id}) is already being managed.")
                return
            job_id = self.vllm_server.start_job()
            if job_id:
                self.vllm_server.running = 1
        elif arg.lower() == 'monitors':
            if self.monitor_server.running:
                print(f"A monitors job ({self.monitor_server.job_id}) is already being managed.")
                return
            # Use the generic start_job() method
            job_id = self.monitor_server.start_job()
            if job_id:
                self.monitor_server.running = 1
        elif arg.lower() == 'chroma':
            if self.chroma_server.running:
                print(f"A Chroma job ({self.chroma_server.job_id}) is already being managed.")
                return
            job_id = self.chroma_server.start_job()
            if job_id:
                self.chroma_server.running = 1
        else:
            print("Invalid command. Usage: start [vllm|monitors|chroma]")

    def do_check(self, arg):
        """
        Checks the status of the job and retrieves its IP address.
        Usage: check [vllm|monitors|chroma]
        """
        if arg.lower() == 'vllm':
            job_id, ip_address, vllm_ready = self.vllm_server.check_status()
            
            if ip_address:
                print("Updating Monitors batch script with VLLM IP address...")
                self.monitor_server.update_vllm_target_in_script(self.vllm_server.ip_address)
                print("-" * 20)
                print(f"State updated: Job ID = {self.vllm_server.job_id}, IP = {self.vllm_server.ip_address}")
                print("-" * 20)

        elif arg.lower() == 'monitors':
            job_id, ip_address, monitor_ready = self.monitor_server.check_status()
            
            if ip_address:
                print("-" * 20)
                print(f"State updated: Job ID = {self.monitor_server.job_id}, IP = {self.monitor_server.ip_address}")
                print("-" * 20)
        
        elif arg.lower() == 'chroma':
            job_id, ip_address, chroma_ready = self.chroma_server.check_status()
            
            if ip_address:
                print("-" * 20)
                print(f"State updated: Job ID = {self.chroma_server.job_id}, IP = {self.chroma_server.ip_address}")
                if chroma_ready:
                    print(f"Chroma server is READY for benchmarking!")
                else:
                    print(f"Chroma server is running but not yet ready. Try checking again.")
                print("-" * 20)
        else:
            print("Invalid command. Usage: check [vllm|monitors|chroma]")

    def do_bench(self, arg):
        """
        Runs a benchmark against the started server.
        Usage: bench [vllm|chroma]
        """
        if arg.lower() == 'vllm':
            if self.vllm_server.ip_address and self.vllm_server.ready:
                self.vllm_server.benchmark_vllm()
            else:
                print("IP address is unknown or server is not ready. Please run 'check vllm' successfully first.")
        
        elif arg.lower() == 'chroma':
            if self.chroma_server.ip_address and self.chroma_server.ready:
                print("\nStarting Chroma benchmark...")
                print("This will test vector ingestion and query performance.")
                self.chroma_server.benchmark_chroma(
                    num_vectors=1000,      # Start with 1k vectors for testing
                    num_queries=100,        # 100 queries
                    dimension=384,          # Standard sentence embedding dimension
                    concurrent_queries=10   # 10 concurrent workers
                )
            else:
                print("IP address is unknown or server is not ready. Please run 'check chroma' successfully first.")
        else:
            print("Invalid command. Usage: bench [vllm|chroma]")

    def do_clean(self, arg):
        """
        Stops all started servers and deletes the logs.
        """
        if self.vllm_server.running:
            self.vllm_server.stop_job()
            self.vllm_server.remove_logs()
    
        if self.monitor_server.running:
            self.monitor_server.stop_job()
            self.monitor_server.remove_logs()
        
        if self.chroma_server.running:
            self.chroma_server.stop_job()
            self.chroma_server.remove_logs()


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