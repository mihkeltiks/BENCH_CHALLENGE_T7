# 🏆 EUMASTER4HPC 2025-2026 Student Challenge: Benchmarking AI Factories on MeluXina Supercomputer

## Project Overview

This project is a **unified benchmarking framework** developed for the **EUMASTER4HPC 2025-2026 Student Challenge**, designed to evaluate end-to-end performance of critical AI Factory components on the **MeluXina supercomputer** in Luxembourg. The framework provides a modular, reproducible solution for benchmarking inference servers, vector databases, and parallel file systems using SLURM orchestration.

**Specification Sources:**
- [GitHub Repository: LuxProvide/EUMASTER4HPC2526](https://github.com/LuxProvide/EUMASTER4HPC2526)
- Project Specification PDF

---

## 🎯 Challenge Objectives & Compliance

The original challenge specification required teams to develop a global benchmarking framework for AI Factory workloads. Below is our compliance matrix:

### Core Requirements

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Benchmark inference servers (vLLM, Triton, etc.) | ✅ | `VLLMServer` class with structured output benchmarking |
| Benchmark vector databases (Chroma, Faiss, Milvus, Weaviate) | ✅ | `ChromaServer` class with OpenLIT instrumentation |
| Benchmark file storage (IO500, Lustre) | ✅ | `LustreServer` class with IO500 suite integration |
| Enable reproducible, modular benchmarking | ✅ | Object-oriented architecture with `SlurmServer` base class |
| SLURM orchestration | ✅ | Batch scripts in `batch_scripts/` directory |
| Prometheus & Grafana monitoring | ✅ | `MonitorServer` class with OpenTelemetry Collector |
| Python modular framework | ✅ | Clean CLI interface with modular server management |

### Phase 2 Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Implement Server class** | `SlurmServer` abstract base class in `src/servers.py` |
| **Implement Client class** | CLI commands act as client to servers |
| **Implement Monitor class** | `MonitorServer` with Grafana/Prometheus |
| **Implement Logging** | Log files per service, `save` command for archiving |
| **Interface for benchmarks** | `CLI` class with `bench` command |
| **Unit tests** | `test/` directory with `unittest` framework |
| **Functional tests** | Integration via CLI command sequences |

### Phase 3 Requirements

| Requirement | Achievement |
|-------------|-------------|
| **Deployment at scale** | Multi-node vLLM with Ray, multi-process IO500 |
| **Performance measurements** | TTFT, TPOT, throughput, bandwidth, IOPS |
| **Resource profiling** | GPU/CPU utilization via Prometheus metrics |
| **Documentation** | README, HowToTest, UML diagrams, this document |

---

## 🏗️ Architecture & Design Choices

### Two-Layer Architecture

The implementation follows a clean separation between user interface and infrastructure management:

```
┌───────────────────────────────────────────────────┐
│  User Interface (cli.py)                          │
│  Commands: start/check/bench/logs/save/stop       │
└─────────────────┬─────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  Python Management Layer                    │
│  - VLLMServer, ChromaServer, MonitorServer, │
│    LustreServer                             │
│  - Inherits from abstract SlurmServer       │
│  - Manages SLURM job lifecycle              │
│  - Implements service-specific benchmarks   │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  SLURM Batch Scripts                        │
│  - start_vllm.sh, start_chroma.sh, etc.     │
│  - Resource allocation (GPU/CPU nodes)      │
│  - Container management (Apptainer/SIF)     │
└─────────────────────────────────────────────┘
```

### Key Design Decisions

#### 1. Abstract Base Class Pattern (`src/servers.py`)

The `SlurmServer` abstract class encapsulates common SLURM job management logic:

- **Job submission** via `sbatch`
- **Job cancellation** via `scancel`
- **Status tracking** via `squeue`
- **Log file management** and IP address discovery
- **State management** (running, ready, job_id, ip_address)

Each concrete service (vLLM, Chroma, Monitors, Lustre) only needs to implement `_check_readiness()` for service-specific health checks.

```python
class SlurmServer(ABC):
    def __init__(self, job_name, script_path, log_dir, log_out_file, log_err_file):
        self.job_id = None
        self.ip_address = None
        self.running = 0
        self.ready = False
        # ...

    @abstractmethod
    def _check_readiness(self):
        """Service-specific readiness check"""
        pass
```

#### 2. Container-Based Deployment (Apptainer/SIF Images)

All services run inside Apptainer containers pulled from registries:

| Container | Purpose |
|-----------|---------|
| `vllm-openai_v0.10.2.sif` | vLLM inference server with GPU support |
| `grafana_latest.sif` | Grafana dashboard for visualization |
| `prometheus_latest.sif` | Prometheus for metrics collection |
| `opentelemetry-collector_0.142.0.sif` | OpenTelemetry for ChromaDB metrics |

This ensures **reproducibility** and **portability** across different HPC environments.

#### 3. Interactive CLI Interface (`src/cli.py`)

A `cmd.Cmd`-based REPL provides intuitive commands:

```bash
bench> start vllm --model meta-llama/Llama-3.1-8B-Instruct --nodes 2
bench> check vllm
bench> bench vllm
bench> logs vllm
bench> stop vllm
```

Available commands:
- `start <service>` - Launch a SLURM job for the service
- `check <service>` - Check status and retrieve IP address
- `bench <service>` - Run benchmarks against the service
- `logs <service>` - Display service logs
- `save <service>` - Archive logs to zip file
- `stop <service>` - Cancel the SLURM job

#### 4. Automatic Service Discovery

Services log their IP addresses with a consistent format (`SLURM_JOB_ID:`, `IP ADDRESS:`), allowing the Python layer to:

- Parse log files for dynamic IP discovery
- Update Prometheus configurations with new targets
- Provide SSH tunnel commands to users for local access

#### 5. Lazy Imports for Fast Startup

Heavy dependencies like `chromadb` and `openlit` are imported only when needed:

```python
def _init_openlit(self, monitor_ip=None):
    import openlit  # Lazy import to speed up CLI startup
```

---

## 🔧 Benchmarking Capabilities

### 1. vLLM Inference Server Benchmarking

**Location:** `src/vllm_server.py`

**Metrics Collected:**
- Latency (end-to-end)
- Throughput (requests/second, tokens/second)
- TTFT (Time-To-First-Token)
- TPOT (Time-Per-Output-Token)
- ITL (Inter-Token Latency)

**Supported Datasets:**
- JSON structured output
- Grammar-based generation
- Regex-constrained output
- Choice-based selection
- xgrammar benchmarks

**Multi-node Support:**
- Pipeline parallelism with Ray across multiple GPU nodes
- Configurable tensor and pipeline parallel sizes
- Dynamic batch script modification for model and node count

**Usage:**
```bash
bench> start vllm --model meta-llama/Llama-3.1-8B-Instruct --nodes 2
bench> check vllm
bench> bench vllm
```

### 2. ChromaDB Vector Database Benchmarking

**Location:** `src/chroma_server.py`

**Operations Tested:**
1. Collection creation
2. Vector insertion (ingestion performance)
3. Sequential query performance (similarity search)
4. Concurrent query performance under load

**Metrics Collected:**
- Ingestion throughput (vectors/second)
- Query latency (mean, p50, p99)
- Concurrent query performance
- Collection creation time

**OpenLIT Integration:**
- Automatic instrumentation of ChromaDB operations
- Metrics exported to OpenTelemetry Collector
- Forwarded to Prometheus for visualization

**Usage:**
```bash
bench> start chroma
bench> start monitors
bench> check chroma
bench> bench chroma
```

### 3. Lustre Parallel File System Benchmarking

**Location:** `src/lustre_server.py`

**IO500 Suite Components:**
- **IOR**: Measures I/O bandwidth (easy and hard workloads)
- **mdtest**: Measures metadata performance (file creation, stat, read, deletion)

**Configurable Parameters:**
- Custom ini configuration files
- Number of MPI processes
- Multi-node scaling

**Usage:**
```bash
bench> start lustre
bench> bench lustre
# Follow prompts for ini file and process count
bench> logs lustre
```

### 4. Unified Monitoring Stack

**Location:** `src/monitor_server.py`

**Components:**
- **Prometheus**: Scrapes vLLM `/metrics` endpoint, receives OpenTelemetry remote writes
- **Grafana**: Pre-built dashboards for visualization
- **OpenTelemetry Collector**: Bridges OpenLIT SDK to Prometheus for ChromaDB metrics

**Pre-built Dashboards:**
- `utils/grafana-dashboards/vllm-dashboard.json`
- `utils/grafana-dashboards/openlit-chromadb-dashboard.json`

**Dynamic Configuration:**
- Prometheus config automatically updated with vLLM target IP
- Hot reload via HTTP API (`/-/reload` endpoint)

---

## 🔬 Technical Highlights

### Dynamic Batch Script Configuration

The `VLLMServer` can modify batch scripts on-the-fly to change model or node count:

```python
def start_job(self, model=None, node_count=None):
    script_to_use = self._modify_batch_script(model=model, node_count=node_count)
    # Submit the modified script
```

### Hot Prometheus Reload

When vLLM starts, its IP is automatically injected into Prometheus configuration:

```python
def update_vllm_prometheus_target(self, vllm_ip_address):
    # Read and update prometheus.yaml with new target
    with open(prometheus_config_path, 'r') as f:
        lines = f.readlines()
    # ... update target IP ...
    self._reload_prometheus()  # POST to /-/reload endpoint
```

### SSH Tunnel Automation

The monitoring server provides ready-to-use SSH tunnel commands:

```python
def _check_readiness(self):
    if self.ip_address:
        print(f"SSH TUNNEL: ssh -p 8822 {self.user}@login.lxp.lu -NL 9090:{self.ip_address}:9090")
        print(f"SSH TUNNEL: ssh -p 8822 {self.user}@login.lxp.lu -NL 3000:{self.ip_address}:3000")
```

### Robust Job Discovery

Jobs are discovered through multiple fallback mechanisms:

1. Parse log files for `SLURM_JOB_ID:` markers
2. Query `squeue` for active jobs matching the job name
3. Verify job is still active before using cached job ID

---

## 🚀 Getting Started

### Prerequisites

1. Access to MeluXina supercomputer
2. SLURM account configured
3. Hugging Face token for model access

### Setup

```bash
# 1. Load modules and set environment
source load_modules.sh
source env.sh

# 2. Pull container images
cd utils/sif-images
./pull_images.sh
cd ../..

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Start the CLI
cd src
python cli.py
```

### Basic Workflow

```bash
# Start monitoring stack
bench> start monitors
bench> check monitors
# Note the SSH tunnel commands and open Grafana locally

# Start and benchmark vLLM
bench> start vllm --model meta-llama/Llama-3.1-8B-Instruct
bench> check vllm
bench> bench vllm

# Start and benchmark ChromaDB
bench> start chroma
bench> check chroma
bench> bench chroma

# Run IO500 Lustre benchmark
bench> bench lustre
```

---

## 🧪 Testing

The project includes unit tests using Python's `unittest` framework with mocked SLURM dependencies:

```bash
# Run all tests
python -m unittest discover test

# Run specific test file
python -m unittest test.test_servers

# Run with verbose output
python -m unittest discover test -v
```

Tests mock external dependencies:
- Subprocess calls (`sbatch`, `scancel`, `squeue`)
- File system operations
- HTTP requests
- Time delays

This ensures tests run quickly without requiring actual SLURM infrastructure.

---

## 🎓 Conclusion

This project successfully delivers a **comprehensive, modular benchmarking framework** that satisfies all challenge requirements:

| Goal | Achievement |
|------|-------------|
| **Modularity** | Abstract class pattern enables easy extension to new services |
| **Reproducibility** | Container-based deployment with versioned SIF images |
| **Observability** | Full metrics pipeline with Prometheus, Grafana, and OpenTelemetry |
| **Usability** | Intuitive CLI with interactive prompts and clear status feedback |
| **Scalability** | Multi-node support for vLLM (Ray) and IO500 (MPI) |
| **Testing** | Mocked unit tests ensure code quality without HPC dependencies |

The framework prepares users for **AI Factory workloads** by providing practical experience with:
- Inference serving at scale
- Vector database operations
- Parallel file system benchmarking
- HPC monitoring and observability

---

## 📚 References

- [EUMASTER4HPC Challenge Repository](https://github.com/LuxProvide/EUMASTER4HPC2526)
- [vLLM Documentation](https://docs.vllm.ai/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [IO500 Benchmark](https://io500.org/)
- [MeluXina User Guide](https://docs.lxp.lu/)
