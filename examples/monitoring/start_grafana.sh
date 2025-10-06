#!/bin/bash -l
#SBATCH -q default
#SBATCH -p cpu
#SBATCH -t 2:0:0
#SBATCH -N 1
#SBATCH -J grafana
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --error=logs/grafana/grafana.err
#SBATCH --output=logs/grafana/grafana.out

module --force purge
module load env/release/2023.1
module load Apptainer/1.3.1-GCCcore-12.3.0

set -x
# Make sure the path to the SIF image is correct
# Here, the SIF image is in the same directory as this script
export SIF_IMAGE=$REPO_SOURCE/utils/sif-images/grafana_latest.sif
export APPTAINER_ARGS="-B ${REPO_SOURCE}/utils/sif-images/grafana_db:/var/lib/grafana"  
export HEAD_HOSTNAME="$(hostname)"
export HEAD_IPADDRESS="$(hostname --ip-address)"


echo "HEAD NODE: ${HEAD_HOSTNAME}"
echo "IP ADDRESS: ${HEAD_IPADDRESS}"
echo "SSH TUNNEL (Execute on your local machine): ssh -p 8822 ${USER}@login.lxp.lu  -NL 3000:${HEAD_IPADDRESS}:3000"  

apptainer run ${APPTAINER_ARGS} ${SIF_IMAGE}
