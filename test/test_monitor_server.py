import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from monitor_server import MonitorServer


class TestMonitorServer(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.server = MonitorServer()
    
    def test_initialization(self):
        """Test that monitor server initializes with correct values"""
        self.assertEqual(self.server.job_name_prefix, "monitors")
        self.assertEqual(self.server.script_path, "../batch_scripts/start_monitors.sh")
        self.assertEqual(self.server.log_dir, "logs/monitors/")
    
    def test_check_readiness_with_ip(self):
        """Test readiness check with IP address"""
        self.server.ip_address = "192.168.1.100"
        
        ready = self.server._check_readiness()
        
        self.assertTrue(ready)
    
    def test_check_readiness_without_ip(self):
        """Test readiness check without IP address"""
        self.server.ip_address = None
        
        ready = self.server._check_readiness()
        
        self.assertFalse(ready)
    
    @patch('builtins.open', new_callable=mock_open, read_data='export VLLM_IP_ADDRESS="old_ip"\n')
    @patch('os.path.exists')
    def test_update_vllm_target_success(self, mock_exists, mock_file):
        """Test updating VLLM IP in script"""
        mock_exists.return_value = True
        
        self.server.update_vllm_target_in_script("192.168.1.200")
        
        # Verify file was opened for reading and writing
        self.assertEqual(mock_file.call_count, 2)
    
    @patch('os.path.exists')
    def test_update_vllm_target_file_not_found(self, mock_exists):
        """Test update when script file doesn't exist"""
        print("\n[TEST] Testing FAILURE scenario: monitor script file not found")
        mock_exists.return_value = False
        
        # Should not raise exception
        self.server.update_vllm_target_in_script("192.168.1.200")
        print("[TEST] ✓ Failure scenario handled correctly")
    
    @patch('builtins.open', new_callable=mock_open, read_data='# No VLLM IP line here\n')
    @patch('os.path.exists')
    def test_update_vllm_target_line_not_found(self, mock_exists, mock_file):
        """Test update when VLLM IP line is not in script"""
        print("\n[TEST] Testing FAILURE scenario: VLLM_IP_ADDRESS line not found in script")
        mock_exists.return_value = True
        
        # Should not raise exception, just warn
        self.server.update_vllm_target_in_script("192.168.1.200")
        
        # File should still be opened
        mock_file.assert_called()
        print("[TEST] ✓ Failure scenario handled correctly")


if __name__ == '__main__':
    unittest.main()
