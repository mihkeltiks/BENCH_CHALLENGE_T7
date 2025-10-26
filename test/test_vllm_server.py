import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from vllm_server import VLLMServer


class TestVLLMServer(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.server = VLLMServer()
    
    def test_initialization(self):
        """Test that VLLM server initializes with correct values"""
        self.assertEqual(self.server.job_name_prefix, "vllm")
        self.assertEqual(self.server.script_path, "../batch_scripts/start_vllm.sh")
        self.assertEqual(self.server.log_dir, "logs/vllm/")
    
    @patch('time.sleep')
    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_check_readiness_success(self, mock_run, mock_exists, mock_sleep):
        """Test successful readiness check"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(
            stdout="Starting vLLM API server 0",
            returncode=0
        )
        
        ready = self.server._check_readiness()
        
        self.assertTrue(ready)
    
    @patch('time.sleep')
    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_check_readiness_not_ready(self, mock_run, mock_exists, mock_sleep):
        """Test when server is not ready"""
        print("\n[TEST] Testing FAILURE scenario: VLLM server not ready after retries")
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(stdout="", returncode=1)
        
        ready = self.server._check_readiness()
        
        self.assertFalse(ready)
        print("[TEST] ✓ Failure scenario handled correctly")
    
    @patch('requests.post')
    def test_benchmark_vllm_no_ip(self, mock_post):
        """Test benchmark without IP address"""
        print("\n[TEST] Testing FAILURE scenario: benchmark without IP address")
        self.server.ip_address = None
        
        # Should not raise exception, just print message
        self.server.benchmark_vllm()
        
        mock_post.assert_not_called()
        print("[TEST] ✓ Failure scenario handled correctly")
    
    @patch('requests.post')
    def test_benchmark_vllm_with_ip(self, mock_post):
        """Test benchmark with valid IP address"""
        self.server.ip_address = "192.168.1.100"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        self.server.benchmark_vllm(num_requests=2)
        
        # Should be called num_requests times
        self.assertEqual(mock_post.call_count, 2)
    
    @patch('requests.post')
    def test_benchmark_vllm_request_failure(self, mock_post):
        """Test benchmark with failed requests"""
        print("\n[TEST] Testing FAILURE scenario: HTTP 500 error during benchmark")
        self.server.ip_address = "192.168.1.100"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        # Should not raise exception
        self.server.benchmark_vllm(num_requests=1)
        
        mock_post.assert_called_once()
        print("[TEST] ✓ Failure scenario handled correctly")


if __name__ == '__main__':
    unittest.main()
