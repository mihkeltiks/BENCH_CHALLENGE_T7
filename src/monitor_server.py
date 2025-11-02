import subprocess
import os
import time
from servers import SlurmServer

class MonitorServer(SlurmServer):
    
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

    def update_vllm_target_in_script(self, vllm_ip_address):
        """
        (This method is specific to MonitorServer and remains unchanged)
        """
        script_path = self.script_path
        print(f"Attempting to update VLLM IP in: {script_path}")
        
        if not os.path.exists(script_path):
            print(f"Error: Monitors script not found at {script_path}")
            return

        try:
            with open(script_path, 'r') as f:
                lines = f.readlines()
            
            updated_lines = []
            updated = False
            target_line_prefix = 'export VLLM_IP_ADDRESS="'

            for line in lines:
                if line.strip().startswith('export VLLM_IP_ADDRESS='):
                    new_line = f'export VLLM_IP_ADDRESS="{vllm_ip_address}" # Updated by CLI\n'
                    updated_lines.append(new_line)
                    updated = True
                    print(f"  -> Replaced VLLM IP with: {vllm_ip_address}")
                else:
                    updated_lines.append(line)

            if updated:
                with open(script_path, 'w') as f:
                    f.writelines(updated_lines)
                print(f"Success! Prometheus batch script updated with VLLM target IP: {vllm_ip_address}")
            else:
                print("Warning: Could not find the 'export VLLM_IP_ADDRESS=' line in the script.")
        except Exception as e:
            print(f"An error occurred while updating the Prometheus script: {e}")

    def update_lustreIO_target_in_script(self, monitor_ip: str):
        """
        Configure the Lustre Server to send metrics to the specified monitor.
        """
        script_path = self.script_path
        print(f"Attempting to update Monitor IP in: {script_path}")

        if not os.path.exists(script_path):
            print(f"Error: Lustre script not found at {script_path}")
            return
        
        try:
            with open(script_path, 'r') as f:
                lines = f.readlines()
            
            updated_lines = []
            updated = False
            target_line_prefix = 'export MONITOR_IP_ADDRESS="'

            for line in lines:
                if line.strip().startswith(target_line_prefix):
                    new_line = f'export MONITOR_IP_ADDRESS="{monitor_ip}" # Updated by CLI\n'
                    updated_lines.append(new_line)
                    updated = True
                    print(f"  -> Replaced Monitor IP with: {monitor_ip}")
                else:
                    updated_lines.append(line)

            if updated:
                with open(script_path, 'w') as f:
                    f.writelines(updated_lines)
                print(f"Success! Lustre batch script updated with Monitor IP: {monitor_ip}")
            else:
                print("No Monitor IP line found to update in the script.")
        except Exception as e:
            print(f"Error updating Lustre script: {e}")