# BENCH_CHALLENGE
Student Challenge 2025-2026 (Benchmarking AI Factories on MeluXina supercomputer)


# Instructions

Run `source env.sh` in the root directory of this repository (where this README is) to set Slurm account names and some base variables that the scripts build on. It will also create a reservation on a GPU node with salloc so you can use Python. Then `module load Python` and `pip install -r requirements.txt`. You also need to pul a vLLM container into the `utils/sif-images` directory.

```
cd utils/sif-images
module load Apptainer/1.3.1-GCCcore-12.3.0
apptainer pull docker://vllm/vllm-openai:latest
```

Then the repo can be used currently like so:

```
python cli.py
> start vllm
> check vllm
> bench vllm
```

# Structure

The planned Python structure looks as follows:
    - interface module: starting servers and clients, conducting benchmarks; logs automatically forwarded to prometheus/grafana; interactive and issue-once workflows
    - server module: general implementation providing commands to start, check and shut down services (storage, database and inference)
    - client module: clients connect to a server and simulate some exemplary workflow
    - benchmark module: uses the clients and servers to simulate 
    - logs module: parses the logs of the clients and servers
    - monitor module: starts grafana/prometheus and receives logs

Planned benchmark capabilities:
    - inference: vLLM, using benchmarks from https://github.com/vllm-project/vllm/tree/main/.buildkite/nightly-benchmarks
    - file storage: lustre - IO500, STREAM. maybe S3 maybe postgres
    - vector datbase: Chroma

