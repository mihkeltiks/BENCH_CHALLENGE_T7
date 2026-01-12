# BENCH_CHALLENGE
Student Challenge 2025-2026 (Benchmarking AI Factories on MeluXina supercomputer)

Full project [Poster](https://github.com/mihkeltiks/BENCH_CHALLENGE_T7/blob/main/docs/BencmarksAI_Poster.pdf) 

# Instructions

Run `source env.sh` in the root directory of this repository (where this README is) to set Slurm account names and some base variables that the scripts build on. It will also create a reservation on a GPU node with salloc so you can use Python. 
Then `module load Python` and `pip install -r requirements.txt`. 

You also need to pull all the related containers into the `utils/sif-images` directory. There is a script in that directory to do that. I initialize `HF\_TOKEN` in my `.bashrc`, you should likely do that as well for simplicity.


Setup works as below:

```
source load_modules.sh
cd utils/sif-images
./pull_images.sh
cd ../../
```

Then the repo can be used currently for example like so:

```
cd src
python cli.py
> start monitors
> start vllm
> check monitors
> check vllm
> bench vllm
```

`start` commands launch Slurm scripts that can be found in the directory `batch_scripts`. 

`check` commands poll the slurm queue and log files to determine whether they are ready and to The line `check vllm` updates the prometheus configuration yaml with the IP of the vLLM master node and issues a reload command so that prometheus starts scraping the correct node for metrics. `check monitors` will print the necessary tunnels that need to be opened so that Grafana and Prometheus can be openend in localhost. The Grafana-Prometheus connection can be configured as described [here](https://docs.vllm.ai/en/v0.7.2/getting_started/examples/prometheus_grafana.html).

To view the logs of the servers, use `logs` followed by the service name, e.g., `logs vllm` or `logs lustre`.
For Lustre, the user is prompted to scroll through previously completed benchmark runs as well as the currently running one for fine grained access.


## Architecture

The implementation follows a two-layer architecture:

```
┌───────────────────────────────────────────────────┐
│  User Interface (cli.py)                          │
│  Commands: start/check/bench chroma/vllm/monitors │
└─────────────────┬─────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  Python Management (service_server.py)      │
│  - service: monitors/vllm/chroma            │
│  - Inherits from SlurmServer                │
│  - Manages SLURM job lifecycle              │
│  - Implements benchmarking logic            │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  SLURM Batch Script (start_service.sh)      │
│  - service: monitors/vllm/chroma            │
│  - Resource allocation                      │
│  - Container management (Apptainer)         │
│  - Server startup                           │
└─────────────────────────────────────────────┘
```

## Benchmark capabilities

When issuing the command `bench vllm`, a structured output serving benchmark is executed against the running vLLM server. This benchmark measures inference performance metrics including latency, throughput, time-to-first-token (TTFT), and time-per-output-token (TPOT). The benchmark supports various dataset types such as JSON, grammar, regex, and choice-based structured outputs, and can be configured with different request rates and concurrency levels.

When issuing the command `bench chroma`, a vector database benchmark is executed against the running ChromaDB server. This benchmark tests collection creation, vector insertion performance (ingestion throughput), query performance for similarity search operations, and concurrent query performance under load. The benchmark uses OpenLIT instrumentation to automatically collect performance metrics, which are forwarded to the OpenTelemetry Collector for monitoring.

When issuing the command `bench lustre`, the IO500 benchmark suite is executed to test parallel file system performance on Lustre. IO500 measures both I/O bandwidth using IOR (for both easy and hard workloads) and metadata performance using mdtest (file creation, stat, read, and deletion operations). This provides comprehensive performance characterization of the Lustre parallel file system under various workloads.


## Displaying metrics

When issuing the command `start monitors`, three different services are started - Grafana, Prometheus and OpenTelemetry Collector. Prometheus is used to receive all the metrics and Grafana to visualize them. The OpenTelemetry Collector is used to measure the performance of the ChromaDB benchmark. The collector passes the metrics forward to Prometheus.

For Hardware Metric Gathering the prometheus configuration is updated on `check monitors` with the currently available IP addresses of the services, including the monitor host.
Data is made available in aggregates on a service basis. The server hosting a service aggregates the hardware data collected through processes running on all associated nodes.
Prometheus reads this data. Labels include the service name, job name, and job id.

In Grafana, Prometheus has to be configured as a data source. If both tunnels are active, this can be simply done by setting the prometheus IP to `localhost:9090`. After that, dashboards have to be generated. These can be imported as json files, which are provided in `utils/grafana-dashboards` for ChromaDB and vLLM. Then, the model that the vLLM serve was configured to serve has to be selected insterted to the `model_name` field as well.
The Hardware Dashboard located in the same folder should display all metrics as soon as prometheus is configured in Grafana.


## Video
Chroma benchmarks:

https://github.com/user-attachments/assets/7cae4834-a882-437a-9c79-21beab3a56da

vLLM benchmarks:

https://github.com/user-attachments/assets/964b28b8-c817-4e61-a400-04a57c790449

Lustre/IO500 benchmarks:

https://github.com/user-attachments/assets/7a6a5600-459f-4966-a8f5-a5b65467f1c5
