#!/bin/bash -l
#SBATCH -q default
#SBATCH -p cpu
#SBATCH -t 2:0:0
#SBATCH -N 1
#SBATCH -J chroma
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --error=logs/chroma/chroma.err
#SBATCH --output=logs/chroma/chroma.out

# module --force purge
# module load env/release/2023.1
# module load Apptainer/1.3.1-GCCcore-12.3.0

set -x
# Log SLURM job ID for tracking
echo "SLURM_JOB_ID: ${SLURM_JOB_ID}"

# Fix pmix error (munge)
export PMIX_MCA_psec=native

# Set up cache directory for Chroma data
export LOCAL_CHROMA_DATA=$REPO_SOURCE/utils/caches/chroma_data
mkdir -p ${LOCAL_CHROMA_DATA}

# Path to the Chroma SIF image
# You'll need to pull/build this image
export SIF_IMAGE=$REPO_SOURCE/utils/sif-images/chroma_latest.sif
export APPTAINER_ARGS="-B ${LOCAL_CHROMA_DATA}:/chroma/chroma"

# Get node information
export HEAD_HOSTNAME="$(hostname)"
export HEAD_IPADDRESS="$(hostname --ip-address)"

# Chroma default port
export CHROMA_PORT=8000

echo "HEAD NODE: ${HEAD_HOSTNAME}"
echo "IP ADDRESS: ${HEAD_IPADDRESS}"
echo "SSH TUNNEL (Execute on your local machine): ssh -p 8822 ${USER}@login.lxp.lu -NL ${CHROMA_PORT}:${HEAD_IPADDRESS}:${CHROMA_PORT}"

# Hardware Metric Scraping
# pip install -r $REPO_SOURCE/requirements.txt
srun --ntasks-per-node=1 --nodes=$SLURM_JOB_NUM_NODES python3 $REPO_SOURCE/src/scraper.py --service-name "$SLURM_JOB_NAME" &

# Start Chroma server
echo "Starting Chroma server on port ${CHROMA_PORT}"
apptainer exec ${APPTAINER_ARGS} ${SIF_IMAGE} chroma run --host 0.0.0.0 --port ${CHROMA_PORT} --path /chroma/chroma
