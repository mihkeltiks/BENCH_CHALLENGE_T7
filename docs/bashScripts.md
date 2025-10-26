# Batch Script Structure

This document describes the structure and conventions used in the SLURM batch scripts for running containerized services on MeluXina.

## Overview

All batch scripts follow a four-section structure:

1. SLURM resource allocation
2. Environment and module loading
3. Container configuration
4. Service execution

## Structure

### Environment Setup

```bash
module --force purge
module load env/release/2023.1
module load Apptainer/1.3.1-GCCcore-12.3.0

set -x
export PMIX_MCA_psec=native  # Fix PMIx errors
```

### Container Configuration

Container images and bind mounts:

```bash
export SIF_IMAGE=$REPO_SOURCE/utils/sif-images/[service]_latest.sif
export APPTAINER_ARGS="-B [host_path]:[container_path]"
```

**Common patterns:**

Data persistence:
```bash
export LOCAL_CACHE=$REPO_SOURCE/utils/caches/[service]
mkdir -p ${LOCAL_CACHE}
export APPTAINER_ARGS="-B ${LOCAL_CACHE}:[mount_point]"
```

Environment variables:
```bash
export APPTAINER_ARGS="--env VAR_NAME=${VALUE}"
```

### Node Information

All scripts log network information for service discovery:

```bash
export HEAD_HOSTNAME="$(hostname)"
export HEAD_IPADDRESS="$(hostname --ip-address)"

echo "HEAD NODE: ${HEAD_HOSTNAME}"
echo "IP ADDRESS: ${HEAD_IPADDRESS}"
```

The Python layer parses these logs to extract IP addresses and establish connections.

## Execution Patterns

### Single-Node Services

```bash
apptainer exec ${APPTAINER_ARGS} ${SIF_IMAGE} [command] [args]
```

### Multi-Node Distributed Services

Coordination pattern for distributed services (e.g., vLLM with Ray):

```bash
# Random port allocation
export RANDOM_PORT=$(python3 -c 'import socket; s = socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')

# Start head node
srun -N 1 -w ${HEAD_HOSTNAME} \
    apptainer exec ${APPTAINER_ARGS} ${SIF_IMAGE} ${HEAD_COMMAND} &

# Start workers
srun -N $(( SLURM_NNODES-1 )) -x ${HEAD_HOSTNAME} \
    apptainer exec ${APPTAINER_ARGS} ${SIF_IMAGE} ${WORKER_COMMAND} &

# Deploy service
apptainer exec ${APPTAINER_ARGS} ${SIF_IMAGE} [service_command]
```

### Multiple Services

For combined services (e.g., Grafana + Prometheus):

```bash
apptainer run ${ARGS1} ${IMAGE1} &

# Dynamic configuration
cat << EOF > ${CONFIG_FILE}
[configuration]
EOF

apptainer run ${ARGS2} ${IMAGE2}
```

## Key Variables

**Standard:**
- `$REPO_SOURCE`: Repository root (set by `env.sh`)
- `$SLURM_NNODES`: Number of allocated nodes
- `$SLURM_CPUS_PER_TASK`: CPUs per task

**Service-specific:**
- vLLM: `$HF_TOKEN`, `$HF_MODEL`, `$TENSOR_PARALLEL_SIZE`, `$PIPELINE_PARALLEL_SIZE`
- Chroma: `$CHROMA_PORT`, `$LOCAL_CHROMA_DATA`
- Monitors: `$VLLM_IP_ADDRESS`, `$PROMETHEUS_DIR`

## Integration with Python

The Python `SlurmServer` classes interact with these scripts through:

1. Job submission: `sbatch [script].sh`
2. Status monitoring: `squeue`
3. Log parsing: `grep 'IP ADDRESS:' [log].out`
4. Service readiness checks

## Adding New Services

1. Create `batch_scripts/start_[service].sh` using the standard structure
2. Implement Python class inheriting from `SlurmServer`
3. Override `_check_readiness()` method
4. Add commands to `cli.py`
5. Update `utils/sif-images/pull_images.sh`
