import subprocess
import os
import time
import requests
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from servers import SlurmServer

class ChromaServer(SlurmServer):
    def __init__(self):
        super().__init__(
            job_name="chroma",
            script_path="../batch_scripts/start_chroma.sh",
            log_dir="logs/chroma/",
            log_out_file="chroma.out",
            log_err_file="chroma.err"
        )

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
        health_url = f"http://{self.ip_address}:{port}/api/v1/heartbeat"
        
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

    def benchmark_chroma(self, port=8000, num_vectors=1000, num_queries=100, dimension=384, concurrent_queries=10):
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
        """
        if not self.ip_address:
            print("Cannot run benchmark without an IP address.")
            return

        base_url = f"http://{self.ip_address}:{port}/api/v1"
        collection_name = "benchmark_collection"
        
        print("=" * 60)
        print(f"Starting Chroma Benchmark")
        print(f"Server: {base_url}")
        print(f"Vectors: {num_vectors}, Queries: {num_queries}, Dimension: {dimension}")
        print("=" * 60)

        try:
            # 1. Create/Get Collection
            print("\n[1/4] Creating collection...")
            start_time = time.time()
            collection_data = {
                "name": collection_name,
                "metadata": {"description": "Benchmark collection"}
            }
            response = requests.post(f"{base_url}/collections", json=collection_data, timeout=30)
            
            if response.status_code in [200, 409]:  # 200 created, 409 already exists
                collection_creation_time = time.time() - start_time
                print(f"✓ Collection ready (took {collection_creation_time:.2f}s)")
            else:
                print(f"✗ Failed to create collection: {response.status_code} - {response.text}")
                return

            # 2. Generate and Insert Vectors
            print(f"\n[2/4] Inserting {num_vectors} vectors...")
            start_time = time.time()
            
            # Generate random vectors
            vectors = np.random.randn(num_vectors, dimension).astype(np.float32).tolist()
            ids = [f"vec_{i}" for i in range(num_vectors)]
            metadatas = [{"index": i, "batch": i // 100} for i in range(num_vectors)]
            
            # Insert in batches (Chroma recommends batch sizes)
            batch_size = 100
            insert_times = []
            
            for i in range(0, num_vectors, batch_size):
                batch_start = time.time()
                batch_end = min(i + batch_size, num_vectors)
                
                add_data = {
                    "ids": ids[i:batch_end],
                    "embeddings": vectors[i:batch_end],
                    "metadatas": metadatas[i:batch_end]
                }
                
                response = requests.post(
                    f"{base_url}/collections/{collection_name}/add",
                    json=add_data,
                    timeout=60
                )
                
                if response.status_code != 201:
                    print(f"✗ Batch {i}-{batch_end} failed: {response.status_code}")
                    continue
                
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
                query_data = {
                    "query_embeddings": [query_vector],
                    "n_results": 10
                }
                
                query_start = time.time()
                response = requests.post(
                    f"{base_url}/collections/{collection_name}/query",
                    json=query_data,
                    timeout=30
                )
                query_time = time.time() - query_start
                
                if response.status_code == 200:
                    query_times.append(query_time)
                    successful_queries += 1
            
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
                    query_vector = np.random.randn(dimension).astype(np.float32).tolist()
                    query_data = {
                        "query_embeddings": [query_vector],
                        "n_results": 10
                    }
                    
                    query_start = time.time()
                    response = requests.post(
                        f"{base_url}/collections/{collection_name}/query",
                        json=query_data,
                        timeout=30
                    )
                    query_time = time.time() - query_start
                    
                    return (response.status_code == 200, query_time)
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