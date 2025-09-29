#!/bin/bash -l
#SBATCH -q default
#SBATCH -p gpu
#SBATCH -t 2:0:0
#SBATCH -N 2
#SBATCH -J vllm
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=128
#SBATCH --gpus-per-task=4
#SBATCH --error=logs/vllm/vllm.err
#SBATCH --output=logs/vllm/vllm.out

module --force purge
module load env/release/2023.1
module load Apptainer/1.3.1-GCCcore-12.3.0

set -x
# Fix pmix error (munge)
export PMIX_MCA_psec=native
# Choose a directory for the cache 
export LOCAL_HF_CACHE=$REPO_SOURCE/utils/caches
mkdir -p ${LOCAL_HF_CACHE}
export HF_TOKEN=""
# Make sure the path to the SIF image is correct
# Here, the SIF image is in the same directory as this script
export SIF_IMAGE=$REPO_SOURCE/utils/sif-images/vllm-openai_latest.sif
export APPTAINER_ARGS=" --nvccli -B ${LOCAL_HF_CACHE}:/root/.cache/huggingface --env HF_HOME=/root/.cache/huggingface --env HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}"  
# Make sure your have been granted access to the model
export HF_MODEL="google/gemma-3-27b-it"

export HEAD_HOSTNAME="$(hostname)"
export HEAD_IPADDRESS="$(hostname --ip-address)"


echo "HEAD NODE: ${HEAD_HOSTNAME}"
echo "IP ADDRESS: ${HEAD_IPADDRESS}"
echo "SSH TUNNEL (Execute on your local machine): ssh -p 8822 ${USER}@login.lxp.lu  -NL 8000:${HEAD_IPADDRESS}:8000"  

# We need to get an available random port
export RANDOM_PORT=$(python3 -c 'import socket; s = socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')

# Command to start the head node
export RAY_CMD_HEAD="ray start --block --head --port=${RANDOM_PORT}"
# Command to start workers
export RAY_CMD_WORKER="ray start --block --address=${HEAD_IPADDRESS}:${RANDOM_PORT}"

export TENSOR_PARALLEL_SIZE=4 # Set it to the number of GPU per node
export PIPELINE_PARALLEL_SIZE=${SLURM_NNODES} # Set it to the number of allocated GPU nodes 

# Start head node
echo "Starting head node"
srun -J "head ray node-step-%J" -N 1 --ntasks-per-node=1  -c $(( SLURM_CPUS_PER_TASK/2 )) -w ${HEAD_HOSTNAME} apptainer exec ${APPTAINER_ARGS} ${SIF_IMAGE} ${RAY_CMD_HEAD} &
sleep 10
echo "Starting worker node"
srun -J "worker ray node-step-%J" -N $(( SLURM_NNODES-1 )) --ntasks-per-node=1 -c ${SLURM_CPUS_PER_TASK} -x ${HEAD_HOSTNAME}  apptainer exec ${APPTAINER_ARGS} ${SIF_IMAGE} ${RAY_CMD_WORKER} &
sleep 30
# Start server on head to serve the model
echo "Starting server"
apptainer exec  ${APPTAINER_ARGS} ${SIF_IMAGE} vllm serve ${HF_MODEL} --tensor-parallel-size ${TENSOR_PARALLEL_SIZE} --pipeline-parallel-size ${PIPELINE_PARALLEL_SIZE}
