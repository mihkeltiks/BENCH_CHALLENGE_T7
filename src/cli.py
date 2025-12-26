import cmd
import sys
from vllm_server import VLLMServer
from monitor_server import MonitorServer
from chroma_server import ChromaServer
from lustre_server import LustreServer

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
        self.lustre_server = LustreServer()

    def do_start(self, arg):
        """
        Starts the service using the sbatch script.
        Usage: 
          start vllm [--model MODEL] [--nodes N]
          start [monitors|chroma|lustre]
        """
        if arg.lower().startswith('vllm'):
            if self.vllm_server.running and self.vllm_server.job_id:
                if self.vllm_server._is_job_active(self.vllm_server.job_id):
                    print(f"A VLLM job ({self.vllm_server.job_id}) is already being managed.")
                    return
                else:
                    # Job is no longer active, reset state
                    print(f"Previous VLLM job ({self.vllm_server.job_id}) is no longer active. Resetting state.")
                    self.vllm_server.running = 0
                    self.vllm_server.job_id = None
                    self.vllm_server.ip_address = None
                    self.vllm_server.ready = False
            
            args = arg.split()
            model = None
            node_count = None
            
            i = 1
            while i < len(args):
                if args[i] == '--model' and i + 1 < len(args):
                    model = args[i + 1]
                    i += 2
                elif args[i] == '--nodes' and i + 1 < len(args):
                    try:
                        node_count = int(args[i + 1])
                        i += 2
                    except ValueError:
                        print(f"Error: Invalid node count: {args[i + 1]}")
                        return
                else:
                    i += 1
            
            job_id = self.vllm_server.start_job(model=model, node_count=node_count)
            if job_id:
                self.vllm_server.running = 1
        elif arg.lower() == 'monitors':
            if self.monitor_server.running:
                print(f"A monitors job ({self.monitor_server.job_id}) is already being managed.")
                return
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
        elif arg.lower() == 'lustre':
            if self.lustre_server.running:
                print(f"A Lustre job ({self.lustre_server.job_id}) is already being managed.")
                print("MultiDir Lustre not yet built")
                return
            job_id = self.lustre_server.start_job()
            if job_id:
                self.lustre_server.running = 1
        else:
            print("Invalid command. Usage: start [vllm|monitors|chroma|lustre]")

    def do_check(self, arg):
        """
        Checks the status of the job and retrieves its IP address.
        Usage: check [vllm|monitors|chroma|lustre]
        """
        if arg.lower() == 'vllm':
            job_id, ip_address, vllm_ready = self.vllm_server.check_status()
            
            if ip_address:
                if self.monitor_server.ip_address:
                    print("Updating Prometheus configuration with vLLM IP...")
                    self.monitor_server.update_vllm_prometheus_target(self.vllm_server.ip_address)
                
                print("-" * 20)
                print(f"State updated: Job ID = {self.vllm_server.job_id}, IP = {self.vllm_server.ip_address}")
                if vllm_ready:
                    print(f"vLLM server is READY for benchmarking!")
                else:
                    print(f"vLLM server is running but not yet ready. Try checking again.")
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
                # print("Updating Monitors batch script with Chroma IP address...")
                # self.monitor_server.update_chroma_target_in_script(self.chroma_server.ip_address)
                print("-" * 20)
                print(f"State updated: Job ID = {self.chroma_server.job_id}, IP = {self.chroma_server.ip_address}")
                if chroma_ready:
                    print(f"Chroma server is READY for benchmarking!")
                else:
                    print(f"Chroma server is running but not yet ready. Try checking again.")
                print("-" * 20)
        
        elif arg.lower() == 'lustre':
            job_id, ip_address, lustre_ready = self.lustre_server.check_status()

            if ip_address:
                # print("Updating Monitors batch script with Lustre IP address...")
                # self.monitor_server.update_lustreIO_target_in_script(self.lustre_server.ip_address)
                print("-" * 20)
                print(f"State updated: Job ID = {self.lustre_server.job_id}, IP = {self.lustre_server.ip_address}")
                if lustre_ready:
                    print(f"Lustre server is READY for benchmarking!")
                else:
                    print(f"Lustre server is running but not yet ready. Try checking again.")
                print("-" * 20)
        else:
            print("Invalid command. Usage: check [vllm|monitors|chroma|lustre]")

    def do_logs(self, arg):
        """
        Displays the logs of the specified service.
        Usage: logs [vllm|monitors|chroma|lustre]
        """
        if arg.lower() == 'vllm':
            self.vllm_server.display_logs()
        elif arg.lower() == 'monitors':
            self.monitor_server.display_logs()
        elif arg.lower() == 'chroma':
            self.chroma_server.display_logs()
        elif arg.lower() == 'lustre':
            self.lustre_server.display_logs()
        else:
            print("Invalid command. Usage: logs [vllm|monitors|chroma|lustre]")

    def do_save(self, arg):
        """
        Saves the logs of the specified service to a file.
        If no service is specified, all are saved, filename is not required.
        Usage: save [vllm|monitors|chroma|lustre] <filename>
        """
        args = arg.split()
        services = ['vllm', 'monitors', 'chroma', 'lustre']
        filename = None
        if len(args) == 0:
            print("Saving logs for all services...")
            # build filename to current timestamp
            filename = f"bench_logs_all_{int(time.time())}.zip"
        elif len(args) == 1:
            if args[0].lower() in services:
                service = args[0].lower()
                filename = f"bench_logs_{service}_{int(time.time())}.zip"
        else:
            user_spec = []
            has_filename = False
            for arg_item in args:
                if arg_item.lower() in services:
                    user_spec.append(arg_item.lower())
                else:
                    if not has_filename:
                        filename = arg_item
                        has_filename = True
                    else:
                        print("Error: unknown argument or possible duplicate filename.")
                        print("First occurence :", filename)
                        print("Second occurence:", arg_item)
                        return
            services = user_spec
        # Now save logs for specified services
        for service in services:
            if service == 'vllm':
                self.vllm_server.save_logs(filename)
            elif service == 'monitors':
                self.monitor_server.save_logs(filename)
            elif service == 'chroma':
                self.chroma_server.save_logs(filename)
            elif service == 'lustre':
                self.lustre_server.save_logs(filename)
        print(f"Logs saved to {filename}")

    def do_bench(self, arg):
        """
        Runs a benchmark against the started server.
        Usage: 
          bench vllm [--num-requests N] [--output-len L] [--max-concurrency C]
          bench chroma [--vectors N] [--queries N] [--dimension N] [--concurrent N]
          bench lustre
        
        ChromaDB benchmark options:
          --vectors, -v N      : Number of vectors to insert (default: 1000)
          --queries, -q N      : Number of queries to run (default: 100)
          --dimension, -d N    : Vector dimension (default: 384)
          --concurrent, -c N   : Concurrent query workers (default: 10)
        """
        if arg.lower().startswith('vllm'):
            if self.vllm_server.ip_address and self.vllm_server.ready:
                # Parse arguments for vllm benchmark
                args = arg.split()
                num_requests = 10
                output_len = 128
                max_concurrency = None
                
                # Parse optional arguments
                i = 1  # Skip 'vllm'
                while i < len(args):
                    if args[i] == '--num-requests' and i + 1 < len(args):
                        num_requests = int(args[i + 1])
                        i += 2
                    elif args[i] == '--output-len' and i + 1 < len(args):
                        output_len = int(args[i + 1])
                        i += 2
                    elif args[i] == '--max-concurrency' and i + 1 < len(args):
                        max_concurrency = int(args[i + 1])
                        i += 2
                    else:
                        i += 1
                
                # Display benchmark parameters
                print(f"\nBenchmark parameters:")
                print(f"  Number of requests: {num_requests}")
                print(f"  Output length: {output_len} tokens")
                print(f"  Max concurrency: {max_concurrency if max_concurrency else 'unlimited'}")
                print()
                
                self.vllm_server.benchmark_vllm(
                    num_requests=num_requests,
                    output_len=output_len,
                    max_concurrency=max_concurrency
                )
            else:
                print("IP address is unknown or server is not ready. Please run 'check vllm' successfully first.")
        
        elif arg.lower().startswith('chroma'):
            # Parse arguments for chroma benchmark
            args = arg.split()
            num_vectors = 1000      # Default: 1k vectors
            num_queries = 100       # Default: 100 queries
            dimension = 384         # Default: standard sentence embedding dimension
            concurrent_queries = 10 # Default: 10 concurrent workers
            
            i = 1  # Skip 'chroma'
            while i < len(args):
                if args[i] in ['--vectors', '-v'] and i + 1 < len(args):
                    try:
                        num_vectors = int(args[i + 1])
                        i += 2
                    except ValueError:
                        print(f"Error: Invalid vector count: {args[i + 1]}")
                        return
                elif args[i] in ['--queries', '-q'] and i + 1 < len(args):
                    try:
                        num_queries = int(args[i + 1])
                        i += 2
                    except ValueError:
                        print(f"Error: Invalid query count: {args[i + 1]}")
                        return
                elif args[i] in ['--dimension', '-d'] and i + 1 < len(args):
                    try:
                        dimension = int(args[i + 1])
                        i += 2
                    except ValueError:
                        print(f"Error: Invalid dimension: {args[i + 1]}")
                        return
                elif args[i] in ['--concurrent', '-c'] and i + 1 < len(args):
                    try:
                        concurrent_queries = int(args[i + 1])
                        i += 2
                    except ValueError:
                        print(f"Error: Invalid concurrent queries: {args[i + 1]}")
                        return
                else:
                    i += 1
            
            # Get monitor server IP if available (for OpenLIT telemetry export)
            monitor_ip = None
            if self.monitor_server.ip_address:
                monitor_ip = self.monitor_server.ip_address
                print(f"OpenLIT will export telemetry to monitoring server: {monitor_ip}")
            else:
                print("Monitor server not running. OpenLIT and grafana monitoring disabled")
            
            if self.chroma_server.ip_address and self.chroma_server.ready:
                print("\nStarting Chroma benchmark...")
                print("This will test vector ingestion and query performance.")
                print(f"Parameters:")
                print(f"  Vectors: {num_vectors}")
                print(f"  Queries: {num_queries}")
                print(f"  Dimension: {dimension}")
                print(f"  Concurrent queries: {concurrent_queries}")
                self.chroma_server.benchmark_chroma(
                    num_vectors=num_vectors,
                    num_queries=num_queries,
                    dimension=dimension,
                    concurrent_queries=concurrent_queries,
                    monitor_ip=monitor_ip
                )
            else:
                print("IP address is unknown or server is not ready. Please run 'check chroma' successfully first.")
        
        elif arg.lower() == 'lustre':
            if self.lustre_server.ip_address and self.lustre_server.ready:
                print("Starting Async IO500 benchmark on lustre server...")
                self.lustre_server.benchmark_lustre()
            else:
                print("IP address is unknown or server is not ready. Please run 'check lustre' successfully first.")
        
        else:
            print("Invalid command. Usage: bench [vllm|chroma|lustre]")

    def do_stop(self, arg):
        """
        Stops the specified service without deleting logs.
        Usage: stop [vllm|monitors|chroma|lustre]
        """
        if arg.lower() == 'vllm':
            self.vllm_server.stop_job()
        elif arg.lower() == 'monitors':
            self.monitor_server.stop_job()
        elif arg.lower() == 'chroma':
            self.chroma_server.stop_job()
        elif arg.lower() == 'lustre':
            self.lustre_server.stop_job()
        elif arg.lower() == 'all':
            print("Stopping all services...")
            self.vllm_server.stop_job()
            self.monitor_server.stop_job()
            self.chroma_server.stop_job()
            self.lustre_server.stop_job()
        else:
            print("Invalid command. Usage: stop [vllm|monitors|chroma|lustre|all]")

    def do_clean(self, arg):
        """
        Stops all started servers and deletes the logs.
        """
        self.clean()

    def clean(self):
        if self.vllm_server.running:
            self.vllm_server.stop_job()
            self.vllm_server.remove_logs()
    
        if self.monitor_server.running:
            self.monitor_server.stop_job()
            self.monitor_server.remove_logs()
        
        if self.chroma_server.running:
            self.chroma_server.stop_job()
            self.chroma_server.remove_logs()
        
        if self.lustre_server.running:
            self.lustre_server.stop_job()
            self.lustre_server.remove_logs()

    def do_exit(self, arg):
        """
        Exits the CLI.
        Usage:
          exit        - Exit without cleaning logs
          exit clean  - Stop all servers, clean logs, then exit
        """
        if arg.lower().strip() == 'clean':
            print("Cleaning up before exit...")
            self.clean()
        
        print("Exiting CLI...")
        print("Goodbye!")
        return True

    def do_EOF(self, arg):
        """
        Exits the CLI on EOF (Ctrl-D) without cleaning.
        """
        print()
        print("Exiting CLI...")
        print("Goodbye!")
        return True

if __name__ == '__main__':
    CLI().cmdloop()