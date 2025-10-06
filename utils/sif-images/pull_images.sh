#!/bin/bash
ml Apptainer/1.3.6-GCCcore-13.3.0
apptainer pull docker://vllm/vllm-openai:latest
apptainer pull docker://prom/prometheus:latest
apptainer pull docker://grafana/grafana:latest

mkdir grafana_db
mkdir prometheus_dir
