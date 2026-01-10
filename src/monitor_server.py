import subprocess
import os
import time
from servers import SlurmServer

class MonitorServer(SlurmServer):
    def update_prometheus_targets(self, ip_map):
        """
        Update Prometheus config with all master node IPs for running services.
        Replaces old job configs and only adds new lines if not present.
        ip_map: dict of job_name -> ip_address
        """
        repo_source = os.getenv('REPO_SOURCE', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prometheus_config_path = os.path.join(repo_source, "utils/prometheus_dir/prometheus.yaml")
        if not os.path.exists(prometheus_config_path):
            print(f"Error: Prometheus config not found at {prometheus_config_path}")
            return
        try:
            with open(prometheus_config_path, 'r') as f:
                lines = f.readlines()
            managed = set(ip_map.keys())
            new_lines = []
            skip = False
            found = {name: False for name in managed}
            i = 0
            while i < len(lines):
                line = lines[i]
                job_match = None
                for name in managed:
                    if f'- job_name: {name}' in line:
                        job_match = name
                        break
                if job_match:
                    # Replace this job block
                    found[job_match] = True
                    # Skip until next job_name or end
                    new_lines.append(f"  - job_name: {job_match}\n")
                    new_lines.append("    static_configs:\n")
                    new_lines.append("      - targets:\n")
                    new_lines.append(f"          - '{ip_map[job_match]}:8010'\n")
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith('- job_name:'):
                        i += 1
                    continue
                new_lines.append(line)
                i += 1
            # Add new jobs not present
            for name, ip in ip_map.items():
                if not found[name]:
                    new_lines.append(f"  - job_name: {name}\n")
                    new_lines.append("    static_configs:\n")
                    new_lines.append("      - targets:\n")
                    new_lines.append(f"          - '{ip}:8010'\n")
            with open(prometheus_config_path, 'w') as f:
                f.writelines(new_lines)
            print(f"✓ Prometheus config updated with master IPs: {ip_map}")
            self._reload_prometheus()
        except Exception as e:
            print(f"Error updating Prometheus config: {e}")
    
    def __init__(self):
        super().__init__(
            job_name="monitors",
            script_path="../batch_scripts/start_monitors.sh",
            log_dir="logs/monitors/",
            log_out_file="monitors.out",
            log_err_file="monitors.err"
        )

    def _check_readiness(self):
        """
        Monitor-specific "readiness" check.
        For monitors, being "ready" just means the IP is found.
        We use this step to print the specific SSH tunnel info.
        """
        if self.ip_address:
            print(f"SSH TUNNEL (Execute on your local machine): ssh -p 8822 {self.user}@login.lxp.lu -NL 9090:{self.ip_address}:9090")
            print(f"SSH TUNNEL (Execute on your local machine): ssh -p 8822 {self.user}@login.lxp.lu -NL 3000:{self.ip_address}:3000")
            return True
        return False


    def update_vllm_prometheus_target(self, vllm_ip_address: str):
        """
        Update the Prometheus config file with the vLLM server IP address and reload Prometheus.
        
        This directly updates the prometheus.yaml file and signals Prometheus to reload.
        """
        if not vllm_ip_address:
            print("Error: vLLM IP address is empty; run 'check vllm' first.")
            return
        
        # Refresh monitor IP before attempting to reload Prometheus
        self.check_status()
        
        if not self.ip_address:
            print("Error: Monitor server IP is unknown. Cannot reload Prometheus.")
            return
        
        repo_source = os.getenv('REPO_SOURCE', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prometheus_config_path = os.path.join(repo_source, "utils/prometheus_dir/prometheus.yaml")
        
        if not os.path.exists(prometheus_config_path):
            print(f"Error: Prometheus config not found at {prometheus_config_path}")
            return
        
        try:
            # Read the current Prometheus config
            with open(prometheus_config_path, 'r') as f:
                lines = f.readlines()
            
            # Update the vLLM target IP
            updated_lines = []
            updated = False
            in_vllm_section = False
            
            for i, line in enumerate(lines):
                if '- job_name: vllm' in line:
                    in_vllm_section = True
                    updated_lines.append(line)
                elif in_vllm_section and '- job_name:' in line:
                    in_vllm_section = False
                    updated_lines.append(line)
                elif in_vllm_section and '- \'' in line and ':8000\'' in line:
                    # This is the vLLM target line
                    new_line = f"          - '{vllm_ip_address}:8000'\n"
                    updated_lines.append(new_line)
                    updated = True
                    print(f"  -> Updated vLLM target to: {vllm_ip_address}:8000")
                else:
                    updated_lines.append(line)
            
            if updated:
                # Write the updated config
                with open(prometheus_config_path, 'w') as f:
                    f.writelines(updated_lines)
                print(f"✓ Prometheus config updated with vLLM IP: {vllm_ip_address}")
                
                # Reload Prometheus
                self._reload_prometheus()
            else:
                print("Warning: Could not find the vLLM target line in prometheus.yaml")
                
        except Exception as e:
            print(f"Error updating Prometheus config for vLLM: {e}")
    
    def _reload_prometheus(self):
        """Send reload signal to Prometheus via HTTP API."""
        try:
            import requests
            reload_url = f"http://{self.ip_address}:9090/-/reload"
            response = requests.post(reload_url, timeout=2)
            if response.status_code == 200:
                print("✓ Prometheus reloaded successfully")
            else:
                print(f"⚠ Prometheus reload returned status {response.status_code}")
                print("  Prometheus will pick up config changes on next scrape cycle (~30s)")
        except requests.exceptions.ConnectionError as e:
            print(f"⚠ Could not reload Prometheus: Connection refused (Prometheus may not be running)")
            print(f"  Check monitors.err for Prometheus startup errors")
            print("  Prometheus will pick up config changes when it starts (~30s after startup)")
        except Exception as e:
            print(f"⚠ Could not reload Prometheus: {e}")
            print("  Prometheus will pick up config changes on next scrape cycle (~30s)")


    # def update_vllm_target_in_script(self, vllm_ip_address):
    #     script_path = self.script_path
    #     print(f"Attempting to update VLLM IP in: {script_path}")
        
    #     if not os.path.exists(script_path):
    #         print(f"Error: Monitors script not found at {script_path}")
    #         return

    #     try:
    #         with open(script_path, 'r') as f:
    #             lines = f.readlines()
            
    #         updated_lines = []
    #         updated = False
    #         target_line_prefix = 'export VLLM_IP_ADDRESS="'

    #         for line in lines:
    #             if line.strip().startswith('export VLLM_IP_ADDRESS='):
    #                 new_line = f'export VLLM_IP_ADDRESS="{vllm_ip_address}" # Updated by CLI\n'
    #                 updated_lines.append(new_line)
    #                 updated = True
    #                 print(f"  -> Replaced VLLM IP with: {vllm_ip_address}")
    #             else:
    #                 updated_lines.append(line)

    #         if updated:
    #             with open(script_path, 'w') as f:
    #                 f.writelines(updated_lines)
    #             print(f"Success! Prometheus batch script updated with VLLM target IP: {vllm_ip_address}")
    #         else:
    #             print("Warning: Could not find the 'export VLLM_IP_ADDRESS=' line in the script.")
    #     except Exception as e:
    #         print(f"An error occurred while updating the Prometheus script: {e}")

    # def update_lustreIO_target_in_script(self, monitor_ip: str):
    #     """
    #     Configure the Lustre Server to send metrics to the specified monitor.
    #     """
    #     script_path = self.script_path
    #     print(f"Attempting to update Monitor IP in: {script_path}")

    #     if not os.path.exists(script_path):
    #         print(f"Error: Lustre script not found at {script_path}")
    #         return
        
    #     try:
    #         with open(script_path, 'r') as f:
    #             lines = f.readlines()
            
    #         updated_lines = []
    #         updated = False
    #         target_line_prefix = 'export MONITOR_IP_ADDRESS="'

    #         for line in lines:
    #             if line.strip().startswith(target_line_prefix):
    #                 new_line = f'export MONITOR_IP_ADDRESS="{monitor_ip}" # Updated by CLI\n'
    #                 updated_lines.append(new_line)
    #                 updated = True
    #                 print(f"  -> Replaced Monitor IP with: {monitor_ip}")
    #             else:
    #                 updated_lines.append(line)

    #         if updated:
    #             with open(script_path, 'w') as f:
    #                 f.writelines(updated_lines)
    #             print(f"Success! Lustre batch script updated with Monitor IP: {monitor_ip}")
    #         else:
    #             print("No Monitor IP line found to update in the script.")
    #     except Exception as e:
    #         print(f"Error updating Lustre script: {e}")

    # def update_chroma_target_in_script(self, chroma_ip_address: str):
    #     """
    #     Update the monitors batch script with the Chroma server IP address so Prometheus/Grafana can scrape it.

    #     Looks for a line beginning with: export CHROMA_IP_ADDRESS="
    #     and replaces its value. If not found, warns the user.
    #     """
    #     script_path = self.script_path
    #     print(f"Attempting to update Chroma IP in: {script_path}")

    #     if not chroma_ip_address:
    #         print("Error: Chroma IP address is empty; run 'check chroma' first.")
    #         return

    #     if not os.path.exists(script_path):
    #         print(f"Error: Monitors script not found at {script_path}")
    #         return

    #     try:
    #         with open(script_path, 'r') as f:
    #             lines = f.readlines()

    #         updated_lines = []
    #         updated = False
    #         target_line_prefix = 'export CHROMA_IP_ADDRESS="'

    #         for line in lines:
    #             if line.strip().startswith('export CHROMA_IP_ADDRESS='):
    #                 new_line = f'export CHROMA_IP_ADDRESS="{chroma_ip_address}" # Updated by CLI\n'
    #                 updated_lines.append(new_line)
    #                 updated = True
    #                 print(f"  -> Replaced CHROMA IP with: {chroma_ip_address}")
    #             else:
    #                 updated_lines.append(line)

    #         if updated:
    #             with open(script_path, 'w') as f:
    #                 f.writelines(updated_lines)
    #             print(f"Success! Monitors batch script updated with Chroma IP: {chroma_ip_address}")
    #         else:
    #             print("Warning: Could not find the 'export CHROMA_IP_ADDRESS=' line in the script.")
    #     except Exception as e:
    #         print(f"An error occurred while updating the monitors script for Chroma: {e}")
