import subprocess
import os
import time
import requests
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from servers import SlurmServer
import openlit
import chromadb

class ChromaServer(SlurmServer):
    def __init__(self):
        super().__init__(
            job_name="chroma",
            script_path="../batch_scripts/start_chroma.sh",
            log_dir="logs/chroma/",
            log_out_file="chroma.out",
            log_err_file="chroma.err"
        )
        self.grafana_ip = None
        self._openlit_initialized = False

    def _check_readiness(self):
        """
        Chroma-specific readiness check.
        Attempts to connect to the Chroma API health endpoint.
        """
        print(f"Checking if Chroma server is ready...")
        
        if not self.ip_address:
            print("No IP address available for readiness check.")
            return False
        
        port = 8000  # Default Chroma port
        health_url = f"http://{self.ip_address}:{port}/api/v2/heartbeat"
        
        for i in range(10):
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    print(f"Chroma server is ready to take requests")
                    return True
            except requests.exceptions.RequestException as e:
                pass
            
            print(f"Server not ready yet, retrying in 5 seconds... (Attempt {i+1}/10)")
            time.sleep(5)
        
        print("Chroma server did not become ready.")
        return False

    def _init_openlit(self, monitor_ip=None, prometheus_port=9090):
        """
        Initialize OpenLIT for ChromaDB instrumentation.
        Should be called before any ChromaDB operations.
        
        Args:
            monitor_ip: IP address of the Prometheus server
                       If provided, OpenLIT will export telemetry to Prometheus OTLP endpoint.
                       If None, will check for OTEL environment variables (e.g., Grafana Cloud).
            prometheus_port: Port for Prometheus web server (default: 9090)
        """
        if self._openlit_initialized:
            return  # Already initialized
        
        import os
        
        # Check if Grafana Cloud or other OTLP endpoint is configured via environment variables
        otlp_endpoint_env = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
        
        if otlp_endpoint_env:
            # Use environment variables (e.g., Grafana Cloud)
            otlp_headers_env = os.getenv('OTEL_EXPORTER_OTLP_HEADERS')
            print(f"Initializing OpenLIT with OTLP endpoint from environment: {otlp_endpoint_env}")
            if otlp_headers_env:
                print(f"  Using OTLP headers from environment (length: {len(otlp_headers_env)})")
            else:
                print("  ⚠ Warning: OTEL_EXPORTER_OTLP_HEADERS not set!")
            
            try:
                openlit.init()  # Will read from OTEL_EXPORTER_OTLP_ENDPOINT and OTEL_EXPORTER_OTLP_HEADERS
                print("  ✓ OpenLIT initialized successfully")
                self._openlit_initialized = True
            except Exception as e:
                print(f"  ✗ Failed to initialize OpenLIT: {e}")
                import traceback
                traceback.print_exc()
                self._openlit_initialized = False
        elif monitor_ip:
            # Use local Prometheus OTLP receiver endpoint
            otlp_endpoint = f"http://{monitor_ip}:{prometheus_port}/api/v1/otlp/v1/metrics"
            print(f"Initializing OpenLIT with Prometheus OTLP endpoint: {otlp_endpoint}")
            openlit.init(otlp_endpoint=otlp_endpoint)
            self._openlit_initialized = True
        else:
            print("No monitor endpoint or OTLP environment variables found. OpenLIT will not be initialized.")
            self._openlit_initialized = False

    def benchmark_chroma(self, port=8000, num_vectors=1000, num_queries=100, dimension=384, 
                        concurrent_queries=10, monitor_ip=None):
        """
        Benchmark Chroma vector database operations.
        
        Tests:
        1. Collection creation
        2. Vector insertion (ingestion performance)
        3. Query performance (similarity search)
        4. Concurrent query performance
        
        Args:
            port: Chroma server port (default: 8000)
            num_vectors: Number of vectors to insert for testing
            num_queries: Number of query operations to perform
            dimension: Dimension of the vectors (default: 384, common for sentence embeddings)
            concurrent_queries: Number of concurrent query workers
            monitor_ip: IP address of monitoring server for OpenLIT telemetry export (optional)
        """
        if not self.ip_address:
            print("Cannot run benchmark without an IP address.")
            return

        # Initialize OpenLIT before any ChromaDB operations
        # Use monitor_ip parameter if provided, otherwise try self.grafana_ip
        monitor_endpoint = monitor_ip or getattr(self, 'grafana_ip', None)
        self._init_openlit(monitor_ip=monitor_endpoint)  


        # Use ChromaDB HttpClient to connect to remote server
        # OpenLIT will automatically instrument all operations
        client = chromadb.HttpClient(host=self.ip_address, port=port)
        collection_name = "benchmark_collection"
        
        print("=" * 60)
        print(f"Starting Chroma Benchmark")
        print(f"Server: {self.ip_address}:{port}")
        print(f"Vectors: {num_vectors}, Queries: {num_queries}, Dimension: {dimension}")
        if monitor_endpoint:
            print(f"OpenLIT monitoring: {monitor_endpoint}")
        print("=" * 60)

        try:
            # 1. Create/Get Collection
            print("\n[1/4] Creating collection...")
            start_time = time.time()
            try:
                # Try to get existing collection first
                collection = client.get_collection(collection_name)
                print(f"  Using existing collection: {collection_name}")
            except Exception:
                # Collection doesn't exist, create it
                collection = client.create_collection(
                    name=collection_name,
                    metadata={"description": "Benchmark collection"}
                )
                print(f"  Created new collection: {collection_name}")
            
            collection_creation_time = time.time() - start_time
            print(f"✓ Collection ready (took {collection_creation_time:.2f}s)")

            # 2. Generate and Insert Vectors
            print(f"\n[2/4] Inserting {num_vectors} vectors...")
            start_time = time.time()
            
            # Generate random vectors
            vectors = np.random.randn(num_vectors, dimension).astype(np.float32).tolist()
            ids = [f"vec_{i}" for i in range(num_vectors)]
            metadatas = [{"index": i, "batch": i // 100} for i in range(num_vectors)]
            
            # Get collection for operations
            collection = client.get_collection(collection_name)
            
            # Insert in batches (Chroma recommends batch sizes)
            batch_size = 100
            insert_times = []
            
            for i in range(0, num_vectors, batch_size):
                batch_start = time.time()
                batch_end = min(i + batch_size, num_vectors)
                
                # Use ChromaDB client API - automatically instrumented by OpenLIT
                collection.add(
                    ids=ids[i:batch_end],
                    embeddings=vectors[i:batch_end],
                    metadatas=metadatas[i:batch_end]
                )
                
                batch_time = time.time() - batch_start
                insert_times.append(batch_time)
                
                if (i + batch_size) % 500 == 0:
                    print(f"  Progress: {i + batch_size}/{num_vectors} vectors inserted")
            
            total_insert_time = time.time() - start_time
            avg_batch_time = np.mean(insert_times) if insert_times else 0
            throughput = num_vectors / total_insert_time if total_insert_time > 0 else 0
            
            print(f"✓ Insertion complete:")
            print(f"  Total time: {total_insert_time:.2f}s")
            print(f"  Avg batch time: {avg_batch_time:.3f}s")
            print(f"  Throughput: {throughput:.2f} vectors/sec")

            # 3. Query Performance (Sequential)
            print(f"\n[3/4] Running {num_queries} sequential queries...")
            start_time = time.time()
            
            query_times = []
            successful_queries = 0
            
            for i in range(num_queries):
                query_vector = np.random.randn(dimension).astype(np.float32).tolist()
                
                query_start = time.time()
                try:
                    # Use ChromaDB client API - automatically instrumented by OpenLIT
                    results = collection.query(
                        query_embeddings=[query_vector],
                        n_results=10
                    )
                    query_time = time.time() - query_start
                    query_times.append(query_time)
                    successful_queries += 1
                except Exception as e:
                    query_time = time.time() - query_start
                    print(f"  Query {i} failed: {e}")
            
            total_query_time = time.time() - start_time
            avg_query_time = np.mean(query_times) if query_times else 0
            p95_query_time = np.percentile(query_times, 95) if query_times else 0
            p99_query_time = np.percentile(query_times, 99) if query_times else 0
            qps = successful_queries / total_query_time if total_query_time > 0 else 0
            
            print(f"✓ Sequential queries complete:")
            print(f"  Successful: {successful_queries}/{num_queries}")
            print(f"  Total time: {total_query_time:.2f}s")
            print(f"  Avg latency: {avg_query_time*1000:.2f}ms")
            print(f"  P95 latency: {p95_query_time*1000:.2f}ms")
            print(f"  P99 latency: {p99_query_time*1000:.2f}ms")
            print(f"  QPS: {qps:.2f} queries/sec")

            # 4. Concurrent Query Performance
            print(f"\n[4/4] Running {num_queries} concurrent queries ({concurrent_queries} workers)...")
            
            def execute_query(query_id):
                try:
                    # Each thread needs its own client connection for thread safety
                    thread_client = chromadb.HttpClient(host=self.ip_address, port=port)
                    thread_collection = thread_client.get_collection(collection_name)
                    
                    query_vector = np.random.randn(dimension).astype(np.float32).tolist()
                    
                    query_start = time.time()
                    # Use ChromaDB client API - automatically instrumented by OpenLIT
                    results = thread_collection.query(
                        query_embeddings=[query_vector],
                        n_results=10
                    )
                    query_time = time.time() - query_start
                    
                    return (True, query_time)
                except Exception as e:
                    return (False, 0)
            
            start_time = time.time()
            concurrent_query_times = []
            concurrent_success_count = 0
            
            with ThreadPoolExecutor(max_workers=concurrent_queries) as executor:
                futures = [executor.submit(execute_query, i) for i in range(num_queries)]
                for future in as_completed(futures):
                    success, query_time = future.result()
                    if success:
                        concurrent_query_times.append(query_time)
                        concurrent_success_count += 1
            
            total_concurrent_time = time.time() - start_time
            avg_concurrent_latency = np.mean(concurrent_query_times) if concurrent_query_times else 0
            p95_concurrent_latency = np.percentile(concurrent_query_times, 95) if concurrent_query_times else 0
            concurrent_qps = concurrent_success_count / total_concurrent_time if total_concurrent_time > 0 else 0
            
            print(f"✓ Concurrent queries complete:")
            print(f"  Successful: {concurrent_success_count}/{num_queries}")
            print(f"  Total time: {total_concurrent_time:.2f}s")
            print(f"  Avg latency: {avg_concurrent_latency*1000:.2f}ms")
            print(f"  P95 latency: {p95_concurrent_latency*1000:.2f}ms")
            print(f"  QPS: {concurrent_qps:.2f} queries/sec")

            # Summary
            print("\n" + "=" * 60)
            print("BENCHMARK SUMMARY")
            print("=" * 60)
            print(f"Ingestion:")
            print(f"  - {num_vectors} vectors in {total_insert_time:.2f}s")
            print(f"  - Throughput: {throughput:.2f} vectors/sec")
            print(f"\nQuery Performance (Sequential):")
            print(f"  - Avg latency: {avg_query_time*1000:.2f}ms")
            print(f"  - P99 latency: {p99_query_time*1000:.2f}ms")
            print(f"  - QPS: {qps:.2f}")
            print(f"\nQuery Performance (Concurrent, {concurrent_queries} workers):")
            print(f"  - Avg latency: {avg_concurrent_latency*1000:.2f}ms")
            print(f"  - P95 latency: {p95_concurrent_latency*1000:.2f}ms")
            print(f"  - QPS: {concurrent_qps:.2f}")
            print("=" * 60)

        except Exception as e:
            print(f"\n✗ Benchmark failed with error: {e}")
            import traceback
            traceback.print_exc()