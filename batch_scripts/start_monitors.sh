#!/bin/bash -l
#SBATCH -q default
#SBATCH -p cpu
#SBATCH -t 2:0:0
#SBATCH -N 1
#SBATCH -J monitors
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --error=logs/monitors/monitors.err
#SBATCH --output=logs/monitors/monitors.out

module --force purge
module load env/release/2023.1
module load Apptainer/1.3.1-GCCcore-12.3.0

set -x
# Log SLURM job ID for tracking
echo "SLURM_JOB_ID: ${SLURM_JOB_ID}"
# Make sure the path to the SIF image is correct
# Here, the SIF image is in the same directory as this script
export GRAFANA_IMAGE=$REPO_SOURCE/utils/sif-images/grafana_latest.sif
export APPTAINER_ARGS="-B ${REPO_SOURCE}/utils/grafana_db:/var/lib/grafana"  
export HEAD_HOSTNAME="$(hostname)"
export HEAD_IPADDRESS="$(hostname --ip-address)"


echo "HEAD NODE: ${HEAD_HOSTNAME}"
echo "IP ADDRESS: ${HEAD_IPADDRESS}"
echo "SSH TUNNEL (Execute on your local machine): ssh -p 8822 ${USER}@login.lxp.lu  -NL 3000:${HEAD_IPADDRESS}:3000"  

apptainer run ${APPTAINER_ARGS} ${GRAFANA_IMAGE} &


# Start OpenTelemetry Collector (intermediary for OpenLIT → Prometheus)
export OTEL_COLLECTOR_IMAGE=$REPO_SOURCE/utils/sif-images/opentelemetry-collector_0.142.0.sif
export OTEL_COLLECTOR_CONFIG=$REPO_SOURCE/utils/otel-collector-config.yaml
export APPTAINER_ARGS="-B ${OTEL_COLLECTOR_CONFIG}:/etc/otelcol/config.yaml"

echo "HEAD NODE: ${HEAD_HOSTNAME}"
echo "IP ADDRESS: ${HEAD_IPADDRESS}"
echo "Starting OpenTelemetry Collector on ports 4317 (gRPC) and 4318 (HTTP)..."

apptainer run ${APPTAINER_ARGS} ${OTEL_COLLECTOR_IMAGE} &

# Give collector a moment to start
sleep 3

export PROMETHEUS_IMAGE=$REPO_SOURCE/utils/sif-images/prometheus_latest.sif
export PROMETHEUS_DIR=${REPO_SOURCE}/utils/prometheus_dir
export APPTAINER_ARGS="-B ${PROMETHEUS_DIR}:/prometheus -B ${PROMETHEUS_DIR}/prometheus.yaml:/etc/prometheus/prometheus.yml" # Mount the config directory
export HEAD_HOSTNAME="$(hostname)"
export HEAD_IPADDRESS="$(hostname --ip-address)"


mkdir -p $PROMETHEUS_DIR

# Use the HEAD_IPADDRESS variable for the vLLM scrape target
cat << EOF > $PROMETHEUS_DIR/prometheus.yaml
global:
  scrape_interval: 5s
  evaluation_interval: 30s

scrape_configs:
  - job_name: vllm
    # The actual IP of the vLLM head node
    static_configs:
      - targets:
          - '0.0.0.0:8000' 

EOF
# ----------------------------------------

echo "HEAD NODE: ${HEAD_HOSTNAME}"
echo "IP ADDRESS: ${HEAD_IPADDRESS}"
echo "SSH TUNNEL (Execute on your local machine): ssh -p 8822 ${USER}@login.lxp.lu  -NL 9090:${HEAD_IPADDRESS}:9090"  

apptainer run ${APPTAINER_ARGS} ${PROMETHEUS_IMAGE} \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/prometheus \
    --web.enable-remote-write-receiver \
    --web.enable-lifecycle