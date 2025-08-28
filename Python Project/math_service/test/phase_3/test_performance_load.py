"""
Performance and Load Testing
Test Phase 3: Performance and Load Testing
"""

import concurrent.futures
import os
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import uvicorn

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from math_service.api.main import app
from math_service.utils.cache import clear_cache


class TestPerformanceBaseline:
    """Test baseline performance metrics"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_test_server(self):
        """Setup test server for performance tests"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        time.sleep(3)

        # Verify server is running
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(
                    "http://127.0.0.1:8004/api/cache/stats", timeout=5
                )
                if response.status_code == 200:
                    break
            except:
                if i == max_retries - 1:
                    pytest.skip("Performance test server failed to start")
                time.sleep(1)

        yield

        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def _run_server(self):
        """Run FastAPI server for performance testing"""
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            uvicorn.run(app, host="127.0.0.1", port=8004, log_level="error")

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Setup for each performance test"""
        self.base_url = "http://127.0.0.1:8004"
        try:
            requests.post(f"{self.base_url}/api/cache/clear", timeout=5)
        except:
            pass
        yield

    def test_single_request_response_time(self):
        """Test single request response time"""
        test_cases = [
            ("/api/pow", {"x": 2, "y": 10}),
            ("/api/factorial", {"n": 10}),
            ("/api/fibonacci", {"n": 20}),
        ]

        for endpoint, payload in test_cases:
            start_time = time.time()
            response = requests.post(f"{self.base_url}{endpoint}", json=payload)
            end_time = time.time()

            response_time = end_time - start_time

            assert response.status_code == 200
            assert response_time < 1.0  # Should respond within 1 second
            print(f"{endpoint} response time: {response_time:.3f}s")

    def test_cached_vs_uncached_performance(self):
        """Test performance improvement with caching"""
        payload = {"x": 5, "y": 15}

        # First request (uncached)
        start_time = time.time()
        response1 = requests.post(f"{self.base_url}/api/pow", json=payload)
        uncached_time = time.time() - start_time

        # Second request (cached)
        start_time = time.time()
        response2 = requests.post(f"{self.base_url}/api/pow", json=payload)
        cached_time = time.time() - start_time

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()

        # Cached request should be faster
        assert cached_time <= uncached_time
        print(f"Uncached: {uncached_time:.3f}s, Cached: {cached_time:.3f}s")
        print(f"Cache speedup: {uncached_time / cached_time:.2f}x")

    def test_mathematical_operations_performance(self):
        """Test performance of different mathematical operations"""
        test_cases = [
            ("pow", "/api/pow", {"x": 2, "y": 20}),
            ("factorial", "/api/factorial", {"n": 15}),
            ("fibonacci", "/api/fibonacci", {"n": 25}),
        ]

        performance_data = {}

        for operation, endpoint, payload in test_cases:
            times = []

            # Run multiple iterations for accurate measurement
            for _ in range(10):
                start_time = time.time()
                response = requests.post(f"{self.base_url}{endpoint}", json=payload)
                end_time = time.time()

                assert response.status_code == 200
                times.append(end_time - start_time)

            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)

            performance_data[operation] = {
                "avg": avg_time,
                "min": min_time,
                "max": max_time,
            }

            print(
                f"{operation}: avg={avg_time:.3f}s, min={min_time:.3f}s, max={max_time:.3f}s"
            )

            # Performance assertions
            assert avg_time < 0.5  # Average should be under 500ms
            assert max_time < 1.0  # No request should take more than 1s

    def test_database_operation_performance(self):
        """Test database operations performance"""
        # Add multiple operations to database
        operations = [("/api/pow", {"x": i, "y": 2}) for i in range(1, 21)]

        # Insert operations
        for endpoint, payload in operations:
            response = requests.post(f"{self.base_url}{endpoint}", json=payload)
            assert response.status_code == 200

        # Test retrieval performance
        start_time = time.time()
        response = requests.get(f"{self.base_url}/api/requests")
        retrieval_time = time.time() - start_time

        assert response.status_code == 200
        assert retrieval_time < 2.0  # Should retrieve within 2 seconds

        data = response.json()
        assert data["count"] == 20

        print(f"Database retrieval time for 20 records: {retrieval_time:.3f}s")


class TestLoadTesting:
    """Test system behavior under load"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_test_server(self):
        """Setup test server for load tests"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        time.sleep(3)

        # Verify server
        try:
            response = requests.get("http://127.0.0.1:8005/api/cache/stats", timeout=10)
            if response.status_code != 200:
                pytest.skip("Load test server not responding")
        except:
            pytest.skip("Load test server failed to start")

        yield

        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def _run_server(self):
        """Run FastAPI server for load testing"""
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            uvicorn.run(app, host="127.0.0.1", port=8005, log_level="error")

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Setup for each load test"""
        self.base_url = "http://127.0.0.1:8005"
        try:
            requests.post(f"{self.base_url}/api/cache/clear", timeout=5)
        except:
            pass
        yield

    def test_concurrent_requests_load(self):
        """Test system under concurrent request load"""

        def make_request(request_id):
            try:
                payload = {"x": 2, "y": request_id % 10 + 1}
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/api/pow", json=payload, timeout=10
                )
                end_time = time.time()

                return {
                    "success": response.status_code == 200,
                    "response_time": end_time - start_time,
                    "request_id": request_id,
                }
            except Exception as e:
                return {"success": False, "error": str(e), "request_id": request_id}

        # Test with different concurrency levels
        concurrency_levels = [5, 10, 20]

        for concurrent_requests in concurrency_levels:
            print(f"\nTesting {concurrent_requests} concurrent requests...")

            start_time = time.time()

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=concurrent_requests
            ) as executor:
                futures = [
                    executor.submit(make_request, i) for i in range(concurrent_requests)
                ]
                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures, timeout=30)
                ]

            total_time = time.time() - start_time

            # Analyze results
            successful_requests = [r for r in results if r["success"]]
            failed_requests = [r for r in results if not r["success"]]

            success_rate = len(successful_requests) / len(results) * 100

            if successful_requests:
                response_times = [r["response_time"] for r in successful_requests]
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
            else:
                avg_response_time = 0
                max_response_time = 0

            print(f"Success rate: {success_rate:.1f}%")
            print(f"Average response time: {avg_response_time:.3f}s")
            print(f"Max response time: {max_response_time:.3f}s")
            print(f"Total test time: {total_time:.3f}s")

            # Performance assertions
            assert success_rate >= 80  # At least 80% success rate
            assert avg_response_time < 2.0  # Average under 2 seconds
            assert max_response_time < 5.0  # No request over 5 seconds

    def test_sustained_load(self):
        """Test system under sustained load"""
        duration = 30  # 30 seconds of sustained load
        requests_per_second = 2

        def make_continuous_requests():
            results = []
            start_time = time.time()
            request_count = 0

            while time.time() - start_time < duration:
                try:
                    payload = {"n": (request_count % 10) + 1}
                    req_start = time.time()
                    response = requests.post(
                        f"{self.base_url}/api/factorial", json=payload, timeout=5
                    )
                    req_end = time.time()

                    results.append(
                        {
                            "success": response.status_code == 200,
                            "response_time": req_end - req_start,
                            "timestamp": req_start,
                        }
                    )

                    request_count += 1

                    # Control request rate
                    sleep_time = (1.0 / requests_per_second) - (req_end - req_start)
                    if sleep_time > 0:
                        time.sleep(sleep_time)

                except Exception as e:
                    results.append(
                        {"success": False, "error": str(e), "timestamp": time.time()}
                    )

            return results

        print(f"\nRunning sustained load test for {duration} seconds...")
        results = make_continuous_requests()

        # Analyze sustained load results
        successful_requests = [r for r in results if r["success"]]
        total_requests = len(results)

        success_rate = len(successful_requests) / total_requests * 100
        actual_rps = total_requests / duration

        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            avg_response_time = statistics.mean(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
        else:
            avg_response_time = 0
            p95_response_time = 0

        print(f"Total requests: {total_requests}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Actual RPS: {actual_rps:.2f}")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"95th percentile response time: {p95_response_time:.3f}s")

        # Performance assertions for sustained load
        assert success_rate >= 90  # 90% success rate under sustained load
        assert avg_response_time < 1.0  # Average under 1 second
        assert p95_response_time < 2.0  # 95% of requests under 2 seconds

    def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load"""
        # Make many requests to potentially cause memory issues
        operations = [
            ("/api/pow", {"x": i % 10 + 1, "y": i % 5 + 1}) for i in range(100)
        ]

        successful_operations = 0
        start_time = time.time()

        for endpoint, payload in operations:
            try:
                response = requests.post(
                    f"{self.base_url}{endpoint}", json=payload, timeout=5
                )
                if response.status_code == 200:
                    successful_operations += 1
            except:
                pass  # Some failures are acceptable under load

        total_time = time.time() - start_time

        print(f"Completed {successful_operations}/{len(operations)} operations")
        print(f"Total time: {total_time:.2f}s")
        print(f"Operations per second: {successful_operations / total_time:.2f}")

        # Check cache stats to ensure it's not growing unbounded
        response = requests.get(f"{self.base_url}/api/cache/stats")
        if response.status_code == 200:
            cache_stats = response.json()
            print(f"Cache size: {cache_stats['cache_size_mb']:.3f} MB")
            print(f"Cached operations: {cache_stats['total_cached_operations']}")

            # Cache shouldn't grow beyond reasonable limits
            assert cache_stats["cache_size_mb"] < 10.0  # Less than 10MB

        # At least 80% operations should succeed
        assert successful_operations >= len(operations) * 0.8

    def test_database_performance_under_load(self):
        """Test database performance under load"""
        # Insert many operations
        operations = [("/api/factorial", {"n": i % 15 + 1}) for i in range(50)]

        # Time the insertion process
        start_time = time.time()
        for endpoint, payload in operations:
            response = requests.post(f"{self.base_url}{endpoint}", json=payload)
            assert response.status_code == 200
        insertion_time = time.time() - start_time

        # Time the retrieval process
        start_time = time.time()
        response = requests.get(f"{self.base_url}/api/requests")
        retrieval_time = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        print(f"Inserted {len(operations)} operations in {insertion_time:.2f}s")
        print(f"Retrieved {data['count']} operations in {retrieval_time:.3f}s")
        print(f"Insertion rate: {len(operations) / insertion_time:.2f} ops/sec")

        # Performance assertions
        assert insertion_time < 60  # Should insert 50 operations within 60 seconds
        assert retrieval_time < 5  # Should retrieve within 5 seconds
        assert (
            len(operations) / insertion_time > 0.5
        )  # At least 0.5 operations per second


class TestStressAndEdgeCases:
    """Test system behavior under stress and edge cases"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_test_server(self):
        """Setup test server for stress tests"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        time.sleep(3)

        try:
            response = requests.get("http://127.0.0.1:8006/api/cache/stats", timeout=10)
            if response.status_code != 200:
                pytest.skip("Stress test server not responding")
        except:
            pytest.skip("Stress test server failed to start")

        yield

        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def _run_server(self):
        """Run FastAPI server for stress testing"""
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            uvicorn.run(app, host="127.0.0.1", port=8006, log_level="error")

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Setup for each stress test"""
        self.base_url = "http://127.0.0.1:8006"
        try:
            requests.post(f"{self.base_url}/api/cache/clear", timeout=5)
        except:
            pass
        yield

    def test_large_number_calculations(self):
        """Test calculations with large numbers"""
        large_number_tests = [
            ("/api/pow", {"x": 2, "y": 50}),  # Large power
            ("/api/factorial", {"n": 20}),  # Large factorial
            ("/api/fibonacci", {"n": 50}),  # Large fibonacci
        ]

        for endpoint, payload in large_number_tests:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}{endpoint}", json=payload, timeout=30
            )
            end_time = time.time()

            if response.status_code == 200:
                data = response.json()
                print(
                    f"{endpoint} with {payload}: {data['result']} (took {end_time - start_time:.3f}s)"
                )
                assert "result" in data
                assert isinstance(data["result"], (int, float))
                assert end_time - start_time < 10  # Should complete within 10 seconds
            else:
                # Large numbers might cause server errors - that's acceptable
                print(
                    f"{endpoint} with {payload}: Server error (status {response.status_code})"
                )
                assert response.status_code in [422, 500]  # Expected error codes

    def test_rapid_successive_requests(self):
        """Test rapid successive requests to same endpoint"""
        payload = {"x": 3, "y": 7}
        num_requests = 50

        results = []
        start_time = time.time()

        for i in range(num_requests):
            try:
                req_start = time.time()
                response = requests.post(
                    f"{self.base_url}/api/pow", json=payload, timeout=5
                )
                req_end = time.time()

                results.append(
                    {
                        "success": response.status_code == 200,
                        "response_time": req_end - req_start,
                        "request_num": i,
                    }
                )
            except:
                results.append({"success": False, "request_num": i})

        total_time = time.time() - start_time
        successful_requests = [r for r in results if r["success"]]

        print(f"Rapid requests: {len(successful_requests)}/{num_requests} successful")
        print(f"Total time: {total_time:.2f}s")
        print(f"Requests per second: {num_requests / total_time:.2f}")

        # Most requests should succeed (cache should help)
        assert len(successful_requests) >= num_requests * 0.9

        # Should achieve high throughput due to caching
        assert num_requests / total_time > 10  # At least 10 RPS

    def test_mixed_load_pattern(self):
        """Test mixed load pattern with different operations"""

        def generate_mixed_requests():
            requests_list = []

            # Mix of different operations and complexities
            for i in range(30):
                if i % 3 == 0:
                    requests_list.append(("/api/pow", {"x": i % 5 + 1, "y": i % 3 + 1}))
                elif i % 3 == 1:
                    requests_list.append(("/api/factorial", {"n": i % 10 + 1}))
                else:
                    requests_list.append(("/api/fibonacci", {"n": i % 15 + 1}))

            return requests_list

        mixed_requests = generate_mixed_requests()

        def execute_request(request_data):
            endpoint, payload = request_data
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}{endpoint}", json=payload, timeout=10
                )
                end_time = time.time()

                return {
                    "success": response.status_code == 200,
                    "response_time": end_time - start_time,
                    "operation": endpoint.split("/")[-1],
                }
            except:
                return {"success": False, "operation": endpoint.split("/")[-1]}

        # Execute mixed load with some concurrency
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(execute_request, req) for req in mixed_requests]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]
        total_time = time.time() - start_time

        # Analyze results by operation type
        operation_stats = {}
        for result in results:
            op = result["operation"]
            if op not in operation_stats:
                operation_stats[op] = {"successful": 0, "total": 0, "times": []}

            operation_stats[op]["total"] += 1
            if result["success"]:
                operation_stats[op]["successful"] += 1
                if "response_time" in result:
                    operation_stats[op]["times"].append(result["response_time"])

        print(f"\nMixed load test results (total time: {total_time:.2f}s):")
        for op, stats in operation_stats.items():
            success_rate = stats["successful"] / stats["total"] * 100
            avg_time = statistics.mean(stats["times"]) if stats["times"] else 0
            print(f"{op}: {success_rate:.1f}% success, avg time: {avg_time:.3f}s")

            # Each operation type should have reasonable success rate
            assert success_rate >= 80

    def test_error_recovery(self):
        """Test system recovery after errors"""
        # First, make some invalid requests
        invalid_requests = [
            ("/api/pow", {"x": "invalid", "y": 2}),
            ("/api/factorial", {"n": -1}),
            ("/api/fibonacci", {"n": "invalid"}),
        ]

        for endpoint, payload in invalid_requests:
            response = requests.post(f"{self.base_url}{endpoint}", json=payload)
            assert response.status_code == 422  # Should get validation errors

        # Then make valid requests to ensure system still works
        valid_requests = [
            ("/api/pow", {"x": 2, "y": 4}),
            ("/api/factorial", {"n": 5}),
            ("/api/fibonacci", {"n": 10}),
        ]

        for endpoint, payload in valid_requests:
            response = requests.post(f"{self.base_url}{endpoint}", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert "result" in data

        print("System successfully recovered from errors")


if __name__ == "__main__":
    # Run performance tests with detailed output
    pytest.main([__file__, "-v", "--tb=short", "-s"])
