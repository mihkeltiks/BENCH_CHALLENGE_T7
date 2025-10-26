import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from io import StringIO

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cli import CLI


class TestCLI(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.cli = CLI()
    
    def test_initialization(self):
        """Test that CLI initializes correctly"""
        self.assertIsNotNone(self.cli.vllm_server)
        self.assertIsNotNone(self.cli.monitor_server)
        self.assertEqual(self.cli.prompt, 'bench> ')
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_do_start_invalid_arg(self, mock_stdout):
        """Test start command with invalid argument"""
        print("\n[TEST] Testing FAILURE scenario: invalid start command argument")
        self.cli.do_start("invalid")
        output = mock_stdout.getvalue()
        self.assertIn("Invalid command", output)
        print("[TEST] ✓ Failure scenario handled correctly")
    
    @patch.object(CLI, 'do_clean')
    def test_do_exit(self, mock_clean):
        """Test exit command"""
        result = self.cli.do_exit(None)
        
        self.assertTrue(result)
        mock_clean.assert_called_once()
    
    @patch.object(CLI, 'do_exit')
    def test_do_EOF(self, mock_exit):
        """Test EOF (Ctrl-D) handling"""
        mock_exit.return_value = True
        
        result = self.cli.do_EOF(None)
        
        self.assertTrue(result)
        mock_exit.assert_called_once()
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_do_start_vllm_already_running(self, mock_stdout):
        """Test starting VLLM when already running"""
        self.cli.vllm_server.running = 1
        self.cli.vllm_server.job_id = "12345"
        
        self.cli.do_start("vllm")
        
        output = mock_stdout.getvalue()
        self.assertIn("already being managed", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_do_start_monitors_already_running(self, mock_stdout):
        """Test starting monitors when already running"""
        self.cli.monitor_server.running = 1
        self.cli.monitor_server.job_id = "67890"
        
        self.cli.do_start("monitors")
        
        output = mock_stdout.getvalue()
        self.assertIn("already being managed", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_do_check_invalid_arg(self, mock_stdout):
        """Test check command with invalid argument"""
        print("\n[TEST] Testing FAILURE scenario: invalid check command argument")
        self.cli.do_check("invalid")
        output = mock_stdout.getvalue()
        self.assertIn("Invalid command", output)
        print("[TEST] ✓ Failure scenario handled correctly")
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_do_bench_invalid_arg(self, mock_stdout):
        """Test bench command with invalid argument"""
        print("\n[TEST] Testing FAILURE scenario: invalid bench command argument")
        self.cli.do_bench("invalid")
        output = mock_stdout.getvalue()
        self.assertIn("Invalid command", output)
        print("[TEST] ✓ Failure scenario handled correctly")
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_do_bench_vllm_not_ready(self, mock_stdout):
        """Test benchmark when VLLM is not ready"""
        print("\n[TEST] Testing FAILURE scenario: benchmark when VLLM not ready")
        self.cli.vllm_server.ip_address = None
        self.cli.vllm_server.ready = False
        
        self.cli.do_bench("vllm")
        
        output = mock_stdout.getvalue()
        self.assertIn("IP address is unknown", output)
        print("[TEST] ✓ Failure scenario handled correctly")


if __name__ == '__main__':
    unittest.main()
