#!/bin/bash
export REPO_SOURCE=$PWD

export SALLOC_ACCOUNT=p200981
export SBATCH_ACCOUNT=p200981
export SLURM_ACCOUNT=p200981

export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp-gateway-prod-eu-central-0.grafana.net/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic MTQ1MDc0OTpnbGNfZXlKdklqb2lNVFl3TURnMk1TSXNJbTRpT2lKemRHRmpheTB4TkRVd056UTVMVzkwYkhBdGQzSnBkR1V0ZEdWemRGOWphSEp2YldFaUxDSnJJam9pTXpFMmJUVkxlbVl6YXpWSFVXbzVaMk5FTlhObmN6TXhJaXdpYlNJNmV5SnlJam9pY0hKdlpDMWxkUzFqWlc1MGNtRnNMVEFpZlgwPQ=="
salloc -t 02:00:00 -q dev -p cpu -N1
