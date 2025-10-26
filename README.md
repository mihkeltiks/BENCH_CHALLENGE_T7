# BENCH_CHALLENGE
Student Challenge 2025-2026 (Benchmarking AI Factories on MeluXina supercomputer)


# Instructions

Run `source env.sh` in the root directory of this repository (where this README is) to set Slurm account names and some base variables that the scripts build on. It will also create a reservation on a GPU node with salloc so you can use Python. Then `module load Python` and `pip install -r requirements.txt`. You also need to pull all the related containers into the `utils/sif-images` directory. There is a script in that directory to do that. I initialize `HF\_TOKEN` in my `.bashrc`, you should likely do that as well for simplicity.


Setup works as below:

```
source load_modules.sh
cd utils/sif-images
./pull_images.sh
cd ../../
```

Then the repo can be used currently like so:

```
cd src
python cli.py
> start vllm
> check vllm # NOTE read below
> start monitors
> check monitors
> bench vllm
```
`start` commands launch Slurm scripts that can be found in the directory `batch_scripts`. The line `check vllm` updates the prometheus configuration yaml with the IP of the vLLM master node. This should be done before starting the monitors so that the results from the vLLM benchmark can be visualized. `check monitors` will print the necessary tunnels that need to be opened so that Grafana and Prometheus can be openend in localhost. The Grafana-Prometheus connection can be configured as described [here](https://docs.vllm.ai/en/v0.7.2/getting_started/examples/prometheus_grafana.html). 

# Structure

The planned Python structure looks as follows:
* interface module: starting servers and clients, conducting benchmarks; logs automatically forwarded to prometheus/grafana; interactive and issue-once workflows
* server module: general implementation providing commands to start, check and shut down services (storage, database and inference)
* client module: clients connect to a server and simulate some exemplary workflow
* benchmark module: uses the clients and servers to simulate 
* logs module: parses the logs of the clients and servers
* monitor module: starts grafana/prometheus and receives logs

Planned benchmark capabilities:
* inference: vLLM, using benchmarks from https://github.com/vllm-project/vllm/tree/main/.buildkite/nightly-benchmarks
* file storage: lustre - IO500, STREAM. maybe S3 maybe postgres
* vector database: Chroma
