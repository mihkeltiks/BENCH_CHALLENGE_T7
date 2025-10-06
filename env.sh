#!/bin/bash
export REPO_SOURCE=$PWD

export SALLOC_ACCOUNT=p200981
export SBATCH_ACCOUNT=p200981
export SLURM_ACCOUNT=p200981

salloc -t 01:00:00 -q dev -p cpu -N1
