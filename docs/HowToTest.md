# Test Suite


## Running Tests

To run all tests:
```bash
python -m unittest discover test
```

To run a specific test file:
```bash
python -m unittest test.test_servers
python -m unittest test.test_vllm_server
python -m unittest test.test_monitor_server
python -m unittest test.test_cli
```

To run with verbose output:
```bash
python -m unittest discover test -v
```

## Test Files

- `test_servers.py` - Tests for the SlurmServer base class
- `test_vllm_server.py` - Tests for the VLLMServer class
- `test_monitor_server.py` - Tests for the MonitorServer class
- `test_cli.py` - Tests for the CLI interface

## Test Coverage

The tests use `unittest.mock` to mock external dependencies like:
- Subprocess calls (sbatch, scancel, squeue, grep)
- File system operations
- HTTP requests
- Time delays

This ensures tests run quickly and don't require actual SLURM infrastructure.
