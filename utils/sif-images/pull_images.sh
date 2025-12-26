#!/bin/bash
ml Apptainer/1.3.6-GCCcore-13.3.0
apptainer pull docker://vllm/vllm-openai:v0.9.2
apptainer pull docker://prom/prometheus:latest
apptainer pull docker://grafana/grafana:latest
apptainer pull docker://chromadb/chroma:latest
apptainer pull docker://otel/opentelemetry-collector:0.142.0

mkdir ../grafana_db
mkdir ../prometheus_dir
mkdir ../caches/chroma_data

# Set up IO500 benchmark
sdir=$(pwd)
cd ..
git clone https://github.com/IO500/io500.git
cd io500
ml env/staging/2024.1 Autotools OpenMPI/5.0.3-GCC-13.3.0 pkgconfig
./prepare.sh
cd $sdir
