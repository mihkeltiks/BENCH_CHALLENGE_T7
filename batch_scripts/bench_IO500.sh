#!/bin/bash -l
#SBATCH -q default
#SBATCH -p gpu
#SBATCH -t 2:0:0
#SBATCH -N 4
#SBATCH -J IO500
#SBATCH --ntasks-per-node=16
#SBATCH --error=logs/IO500/IO500.err
#SBATCH --output=logs/IO500/IO500.out

module --force purge
module load env/release/2023.1
module load Apptainer/1.3.1-GCCcore-12.3.0 Python

set -x

export IO500_ROOT=$REPO_SOURCE/utils/io500

num_procs=64
ini_file="io500.ini"

srun --ntasks=$num_procs $IO500_ROOT/io500 $ini_file