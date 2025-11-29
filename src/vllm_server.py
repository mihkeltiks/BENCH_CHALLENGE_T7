import subprocess
import os
import time
import re
import requests
from datetime import datetime
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
        self.current_model = "google/gemma-3-27b-it"
        self.current_node_count = None
        self.temp_script_path = None  # Track temporary script for cleanup

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

    def _modify_batch_script(self, model=None, node_count=None):
        """
        Modify the batch script with new model and/or node count.
        Creates a temporary modified version of the script.
        
        Returns:
            str: Path to the modified script (or original if no changes)
        """
        # Get absolute path to the original script
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        original_script = os.path.join(project_root, self.script_path.lstrip('../'))
        
        if not model and not node_count:
            # No changes needed, return original
            return original_script
        
        # Read the original script
        with open(original_script, 'r') as f:
            script_content = f.read()
        
        # Track if we made changes
        modified = False
        
        # Modify node count if provided
        if node_count is not None:
            # Replace #SBATCH -N line
            pattern = r'#SBATCH -N \d+'
            replacement = f'#SBATCH -N {node_count}'
            if re.search(pattern, script_content):
                script_content = re.sub(pattern, replacement, script_content)
                modified = True
                self.current_node_count = node_count
                print(f"Updated node count to {node_count}")
        
        # Modify model if provided
        if model is not None:
            # Replace export HF_MODEL line
            pattern = r'export HF_MODEL="[^"]*"'
            replacement = f'export HF_MODEL="{model}"'
            if re.search(pattern, script_content):
                script_content = re.sub(pattern, replacement, script_content)
                modified = True
                self.current_model = model
                print(f"Updated model to {model}")
        
        if not modified:
            return original_script
        
        # Write modified script to a temporary location
        script_dir = os.path.dirname(original_script)
        temp_script = os.path.join(script_dir, "start_vllm_temp.sh")
        
        with open(temp_script, 'w') as f:
            f.write(script_content)
        
        # Make it executable
        os.chmod(temp_script, 0o755)
        
        # Store path for cleanup
        self.temp_script_path = temp_script
        
        return temp_script

    def start_job(self, model=None, node_count=None):
        """
        Starts the sbatch script and returns the job ID.
        
        Args:
            model: Model name to use (e.g., "google/gemma-3-27b-it")
            node_count: Number of nodes to allocate (e.g., 2)
        """
        # Reset temp script path
        self.temp_script_path = None
        
        # Store model if provided (before modifying script, so it's always set)
        if model is not None:
            self.current_model = model
        
        # Modify batch script if parameters provided
        script_to_use = self._modify_batch_script(model=model, node_count=node_count)
        
        print(f"Starting {self.job_name_prefix} service via sbatch...")
        if model:
            print(f"  Model: {model}")
        if node_count:
            print(f"  Node count: {node_count}")
        
        try:
            result = subprocess.run(
                ["sbatch", script_to_use],
                capture_output=True,
                text=True,
                check=True
            )
            self.job_id = result.stdout.strip().split()[-1]
            print(f"{self.job_name_prefix} script submitted. Job ID: {self.job_id}")
            
            # Clean up temporary script after successful submission
            self._cleanup_temp_script()
            
            return self.job_id
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError) as e:
            print(f"Error starting {self.job_name_prefix} job: {e}")
            # Clean up temporary script even on error
            self._cleanup_temp_script()
            return None
    
    def _cleanup_temp_script(self):
        """Remove temporary script file if it exists."""
        if self.temp_script_path and os.path.exists(self.temp_script_path):
            try:
                os.remove(self.temp_script_path)
                print(f"Cleaned up temporary script: {self.temp_script_path}")
            except OSError as e:
                print(f"Warning: Could not remove temporary script {self.temp_script_path}: {e}")
            finally:
                self.temp_script_path = None

    def benchmark_vllm(self, port=8000, num_requests=10, model="google/gemma-3-27b-it", 
                       dataset="json", output_len=128, request_rate=float("inf"),
                       max_concurrency=None, structured_output_ratio=1.0):
        """
        Runs the vLLM structured output benchmark script.
        
        Args:
            port: Port number for the vLLM server (default: 8000)
            num_requests: Number of prompts to process (default: 10)
            model: Model name (default: "google/gemma-3-27b-it", will use model from startup if set)
            dataset: Dataset type - "json", "json-unique", "grammar", "regex", "choice", or "xgrammar_bench" (default: "json")
            output_len: Number of output tokens (default: 128)
            request_rate: Requests per second (default: inf for all at once)
            max_concurrency: Maximum concurrent requests (default: None)
            structured_output_ratio: Ratio of structured output requests (default: 1.0)
        """
        if not self.ip_address:
            print("Cannot run benchmark without an IP address.")
            return
        
        # Use the model selected during startup if one was set and default is being used
        if self.current_model and model == "google/gemma-3-27b-it":
            model = self.current_model
            print(f"Using model from startup: {model}")

        # Get the absolute path to the benchmark script
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        benchmark_script = os.path.join(script_dir, "benchmarks", "benchmark_serving_structured_output.py")
        
        if not os.path.exists(benchmark_script):
            print(f"Error: Benchmark script not found at {benchmark_script}")
            return

        print(f"Starting vLLM structured output benchmark...")
        print(f"  Model: {model}")
        print(f"  Server: {self.ip_address}:{port}")
        print(f"  Dataset: {dataset}")
        print(f"  Number of prompts: {num_requests}")
        print(f"  Output length: {output_len} tokens")
        
        # Create results directory as absolute path (relative to project root)
        # Since benchmark runs from benchmarks/ directory, we need absolute path
        if os.path.isabs(self.log_dir):
            results_dir = os.path.join(self.log_dir, "benchmark_results")
        else:
            # Make it relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            results_dir = os.path.join(project_root, 'src', self.log_dir, "benchmark_results")
        
        # Create the directory if it doesn't exist
        os.makedirs(results_dir, exist_ok=True)
        
        # Generate filename with benchmark parameters
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_short = model.replace("/", "_").replace("-", "_")
        max_conc_str = f"mc{max_concurrency}" if max_concurrency else "mcunlimited"
        filename = f"benchmark_{model_short}_n{num_requests}_ol{output_len}_{max_conc_str}_ds{dataset}_{timestamp}.json"
        
        # Build command arguments
        cmd = [
            "python",
            "../benchmarks/benchmark_serving_structured_output.py",
            "--backend", "vllm",
            "--host", self.ip_address,
            "--port", str(port),
            "--model", model,
            "--dataset", dataset,
            "--num-prompts", str(num_requests),
            "--output-len", str(output_len),
            "--structured-output-ratio", str(structured_output_ratio),
            "--save-results",
            "--result-dir", results_dir,
            "--result-filename", filename,
        ]
        
        if request_rate != float("inf"):
            cmd.extend(["--request-rate", str(request_rate)])
        
        if max_concurrency:
            cmd.extend(["--max-concurrency", str(max_concurrency)])
        
        # Add endpoint for completions API
        cmd.extend(["--endpoint", "/v1/completions"])
        
        print(f"\nExecuting: {' '.join(cmd)}\n")
        print(f"Results will be saved to: {os.path.join(results_dir, filename)}\n")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=os.path.dirname(benchmark_script),
                check=False,
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                print("\n" + "-" * 50)
                print("Benchmark completed successfully!")
                print(f"Results saved to: {os.path.join(results_dir, filename)}")
                print("-" * 50)
            else:
                print(f"\nBenchmark exited with code {result.returncode}")
                print(f"Results may still be available at: {os.path.join(results_dir, filename)}")
                
        except FileNotFoundError:
            print(f"Error: Python3 not found or benchmark script is missing.")
        except Exception as e:
            print(f"Error running benchmark: {e}")