#!/bin/bash -l
#SBATCH -q default
#SBATCH -p gpu
#SBATCH -t 2:0:0
#SBATCH -N 1
#SBATCH -J lustreIO
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --error=logs/lustre/lustre.err
#SBATCH --output=logs/lustre/lustre.out

module --force purge
module load env/release/2023.1
module load Apptainer/1.3.1-GCCcore-12.3.0 Python

pip install -r $REPO_SOURCE/requirements.txt

set -x
# Log SLURM job ID for tracking
echo "SLURM_JOB_ID: ${SLURM_JOB_ID}"

# Fix pmix error (munge)
export PMIX_MCA_psec=native

LUSTRE_DIR=$PROJECT/utils/lustre_test_dir

echo "Starting Lustre Server on given directory"

export STRIPE_COUNT=4
export STRIPE_SIZE=1M
export START_OST=0

echo "Lustre directory: ${LUSTRE_DIR}"
echo "IP ADDRESS: $(hostname --ip-address)"

# check if directory is given as argument
if [ -n "$1" ]; then
    LUSTRE_DIR="$1"
else
    mkdir -p ${LUSTRE_DIR}
    # lfs setstripe -C ${STRIPE_COUNT} -s ${STRIPE_SIZE} -o ${START_OST} ${LUSTRE_DIR}
    lfs setstripe -c 1 ${LUSTRE_DIR}
fi

ln -s $LUSTRE_DIR $REPO_SOURCE/utils/lustre_test_dir

## Start scraping lustre info of the given directory

python $REPO_SOURCE/src/lustre_scraper.py --lustre-dir ${LUSTRE_DIR}
