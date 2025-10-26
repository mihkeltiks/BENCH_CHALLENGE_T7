import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from servers import SlurmServer


class MockServer(SlurmServer):
    """Concrete implementation of abstract SlurmServer for testing"""
    def __init__(self):
        super().__init__(
            job_name="test",
            script_path="/tmp/test.sh",
            log_dir="/tmp/logs/",
            log_out_file="test.out",
            log_err_file="test.err"
        )
    
    def _check_readiness(self):
        return True


class TestSlurmServer(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.server = MockServer()
    
    def test_initialization(self):
        """Test that server initializes with correct values"""
        self.assertIsNone(self.server.job_id)
        self.assertIsNone(self.server.ip_address)
        self.assertEqual(self.server.running, 0)
        self.assertFalse(self.server.ready)
        self.assertEqual(self.server.job_name_prefix, "test")
    
    @patch('subprocess.run')
    def test_start_job_success(self, mock_run):
        """Test successful job start"""
        mock_run.return_value = MagicMock(stdout="Submitted batch job 12345")
        
        job_id = self.server.start_job()
        
        self.assertEqual(job_id, "12345")
        self.assertEqual(self.server.job_id, "12345")
        mock_run.assert_called_once_with(
            ["sbatch", "/tmp/test.sh"],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('subprocess.run')
    def test_start_job_failure(self, mock_run):
        """Test job start failure"""
        print("\n[TEST] Testing FAILURE scenario: sbatch command not found")
        mock_run.side_effect = FileNotFoundError("sbatch not found")
        
        job_id = self.server.start_job()
        
        self.assertIsNone(job_id)
        print("[TEST] ✓ Failure scenario handled correctly")
    
    @patch('subprocess.run')
    def test_stop_job_success(self, mock_run):
        """Test successful job stop"""
        self.server.job_id = "12345"
        self.server.running = 1
        
        self.server.stop_job()
        
        mock_run.assert_called_once_with(
            ["scancel", "12345"],
            check=True,
            capture_output=True
        )
        self.assertEqual(self.server.running, 0)
        self.assertIsNone(self.server.job_id)
    
    def test_stop_job_no_job_id(self):
        """Test stop job with no job ID"""
        self.server.job_id = None
        
        # Should not raise exception
        self.server.stop_job()
        self.assertIsNone(self.server.job_id)
    
    @patch('os.path.exists')
    @patch('os.remove')
    def test_remove_logs(self, mock_remove, mock_exists):
        """Test log file removal"""
        mock_exists.return_value = True
        
        self.server.remove_logs()
        
        self.assertEqual(mock_remove.call_count, 2)
    
    @patch('subprocess.run')
    def test_find_job_id_success(self, mock_run):
        """Test finding job ID via squeue"""
        mock_run.return_value = MagicMock(
            stdout="12345 test-job\n67890 other-job",
            returncode=0
        )
        
        with patch.dict(os.environ, {'USER': 'testuser'}):
            server = MockServer()
            job_id = server._find_job_id()
        
        self.assertEqual(job_id, "12345")
    
    @patch('subprocess.run')
    def test_find_job_id_not_found(self, mock_run):
        """Test when job ID is not found"""
        print("\n[TEST] Testing FAILURE scenario: job ID not found in squeue")
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        
        job_id = self.server._find_job_id()
        
        self.assertIsNone(job_id)
        print("[TEST] ✓ Failure scenario handled correctly")
    
    @patch('time.sleep')
    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_find_ip_address_success(self, mock_run, mock_exists, mock_sleep):
        """Test finding IP address from log"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(
            stdout="IP ADDRESS: 192.168.1.100",
            returncode=0
        )
        
        ip = self.server._find_ip_address()
        
        self.assertEqual(ip, "192.168.1.100")
    
    @patch('time.sleep')
    @patch('os.path.exists')
    def test_find_ip_address_not_found(self, mock_exists, mock_sleep):
        """Test when IP address is not found"""
        print("\n[TEST] Testing FAILURE scenario: IP address not found in log file")
        mock_exists.return_value = False
        
        ip = self.server._find_ip_address()
        
        self.assertIsNone(ip)
        print("[TEST] ✓ Failure scenario handled correctly")


if __name__ == '__main__':
    unittest.main()
