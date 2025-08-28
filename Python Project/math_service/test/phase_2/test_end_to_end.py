"""
End-to-End Integration Tests
Test Phase 2: End-to-End Integration Testing
"""

import os
import socket
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
from math_service.db.sqlite_handler import get_all_operations, init_db
from math_service.utils.cache import clear_cache


class TestEndToEndIntegration:
    """End-to-end integration tests covering full workflows"""

    @classmethod
    def setup_class(cls):
        """Setup test server for E2E tests with better error handling"""
        print("Setting up E2E test server...")

        # Create temporary database
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        cls.temp_db.close()

        # Find a free port for the server
        cls.server_port = cls._find_free_port(8003)  # Start from 8003
        cls.base_url = f"http://127.0.0.1:{cls.server_port}"

        print(f"Starting E2E server on port {cls.server_port}")

        # Start test server in background thread
        cls.server_thread = threading.Thread(target=cls._run_server, daemon=True)
        cls.server_thread.start()

        # Wait for server to be ready with proper checking
        if not cls._wait_for_server():
            pytest.skip("Test server failed to start properly")

        print(f"✓ E2E test server ready at {cls.base_url}")

    @classmethod
    def _find_free_port(cls, start_port=8003, max_attempts=20):
        """Find a free port starting from start_port"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                    print(f"Found free port for E2E: {port}")
                    return port
            except OSError:
                continue
        raise RuntimeError(f"Could not find a free port starting from {start_port}")

    @classmethod
    def _run_server(cls):
        """Run FastAPI server for testing"""
        try:
            print(f"Starting E2E FastAPI server on port {cls.server_port}")
            with patch("math_service.db.sqlite_handler.DB_FILE", cls.temp_db.name):
                uvicorn.run(
                    app,
                    host="127.0.0.1",
                    port=cls.server_port,
                    log_level="error",
                    access_log=False,
                )
        except Exception as e:
            print(f"E2E Server failed to start: {e}")

    @classmethod
    def _wait_for_server(cls, timeout=30):
        """Wait for the server to be ready to accept connections"""
        print(f"Waiting for E2E server to be ready at {cls.base_url}")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try multiple endpoints to ensure server is fully ready
                test_endpoints = [
                    "/",  # Main page
                    "/api/cache/stats",  # Cache stats endpoint
                ]

                for endpoint in test_endpoints:
                    response = requests.get(f"{cls.base_url}{endpoint}", timeout=3)
                    if response.status_code not in [
                        200,
                        404,
                    ]:  # 404 is ok for some endpoints
                        raise requests.exceptions.RequestException(
                            f"Bad status: {response.status_code}"
                        )

                print("✓ E2E server is ready and responding")
                return True

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                # Server not ready yet, wait a bit
                time.sleep(1)
                continue
            except Exception as e:
                print(f"Unexpected error checking E2E server: {e}")
                time.sleep(1)
                continue

        # If we get here, server didn't start in time
        print(f"E2E server failed to start within {timeout} seconds")
        return False

    @classmethod
    def _check_server_health(cls):
        """Check if server is still responding"""
        try:
            response = requests.get(f"{cls.base_url}/api/cache/stats", timeout=5)
            return response.status_code == 200
        except:
            return False

    @classmethod
    def teardown_class(cls):
        """Cleanup after all tests"""
        print("Tearing down E2E test server...")

        # Cleanup database
        if hasattr(cls, "temp_db") and os.path.exists(cls.temp_db.name):
            os.unlink(cls.temp_db.name)
            print("E2E temporary database cleaned up")

    def setup_method(self):
        """Setup for each test method"""
        # Check if server is still running
        if not self._check_server_health():
            pytest.skip(f"E2E server is not responding at {self.base_url}")

        # Clear cache before each test
        try:
            response = requests.post(f"{self.base_url}/api/cache/clear", timeout=5)
            if response.status_code != 200:
                print(f"Warning: Cache clear returned {response.status_code}")
        except Exception as e:
            print(f"Warning: Could not clear cache: {e}")

    def teardown_method(self):
        """Cleanup after each test method"""
        # Clear cache after each test
        try:
            requests.post(f"{self.base_url}/api/cache/clear", timeout=5)
        except:
            pass  # Ignore cleanup errors

    def test_complete_calculation_workflow(self):
        """Test complete calculation workflow from API to database"""
        # Step 1: Perform calculations via API
        test_operations = [
            ("/api/pow", {"x": 2, "y": 8}),
            ("/api/factorial", {"n": 6}),
            ("/api/fibonacci", {"n": 12}),
            ("/api/pow", {"x": 3, "y": 4}),
            ("/api/factorial", {"n": 7}),
        ]

        results = []
        for endpoint, payload in test_operations:
            response = requests.post(f"{self.base_url}{endpoint}", json=payload)
            assert response.status_code == 200
            data = response.json()
            results.append(data)

        # Verify calculations are correct
        assert results[0]["result"] == 256  # 2^8
        assert results[1]["result"] == 720  # 6!
        assert results[2]["result"] == 144  # fibonacci(12)
        assert results[3]["result"] == 81  # 3^4
        assert results[4]["result"] == 5040  # 7!

        # Step 2: Verify all operations are saved in database
        response = requests.get(f"{self.base_url}/api/requests")
        assert response.status_code == 200

        db_data = response.json()
        assert db_data["count"] == 5

        # Step 3: Verify operations can be filtered
        # Filter by operation type
        response = requests.get(f"{self.base_url}/api/requests?operation_filter=pow")
        assert response.status_code == 200
        pow_data = response.json()
        assert pow_data["count"] == 2  # Two pow operations

        # Filter by input
        response = requests.get(f"{self.base_url}/api/requests?input_filter=6")
        assert response.status_code == 200
        filtered_data = response.json()
        assert filtered_data["count"] >= 1  # At least factorial(6)

    def test_cache_effectiveness_workflow(self):
        """Test cache effectiveness in reducing database saves"""
        # Step 1: Make initial request (should save to DB)
        payload = {"x": 5, "y": 3}
        response1 = requests.post(f"{self.base_url}/api/pow", json=payload)
        assert response1.status_code == 200
        result1 = response1.json()

        # Step 2: Get initial DB stats
        response = requests.get(f"{self.base_url}/api/database/stats")
        assert response.status_code == 200
        initial_stats = response.json()
        initial_total = initial_stats["total_operations"]

        # Step 3: Make same request again (should hit cache)
        response2 = requests.post(f"{self.base_url}/api/pow", json=payload)
        assert response2.status_code == 200
        result2 = response2.json()

        # Results should be identical
        assert result1 == result2

        # Step 4: Verify DB didn't get another save
        response = requests.get(f"{self.base_url}/api/database/stats")
        assert response.status_code == 200
        final_stats = response.json()
        final_total = final_stats["total_operations"]

        # Total operations should be the same (cache prevented duplicate save)
        assert final_total == initial_total

        # Step 5: Verify cache stats show the operation
        response = requests.get(f"{self.base_url}/api/cache/stats")
        assert response.status_code == 200
        cache_stats = response.json()
        assert cache_stats["total_cached_operations"] >= 1

    def test_different_input_same_operation_workflow(self):
        """Test same operation with different inputs"""
        # Perform multiple pow operations with different inputs
        pow_operations = [
            {"x": 2, "y": 1},
            {"x": 2, "y": 2},
            {"x": 2, "y": 3},
            {"x": 2, "y": 4},
            {"x": 2, "y": 5},
        ]

        expected_results = [2, 4, 8, 16, 32]

        for i, payload in enumerate(pow_operations):
            response = requests.post(f"{self.base_url}/api/pow", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == expected_results[i]

        # Verify all operations are saved uniquely
        response = requests.get(f"{self.base_url}/api/requests?operation_filter=pow")
        assert response.status_code == 200
        pow_data = response.json()
        assert pow_data["count"] == 5

        # Verify each has different results
        results = [item["result"]["result"] for item in pow_data["data"]]
        assert sorted(results) == sorted(expected_results)

    def test_mixed_operations_with_cache_clear_workflow(self):
        """Test workflow with cache clearing to create database duplicates"""
        print("Testing mixed operations with cache clearing...")

        # First set of operations
        workflow_steps_1 = [
            ("/api/pow", {"x": 2, "y": 4}, 16),
            ("/api/factorial", {"n": 4}, 24),
            ("/api/fibonacci", {"n": 8}, 21),
        ]

        for endpoint, payload, expected in workflow_steps_1:
            response = requests.post(
                f"{self.base_url}{endpoint}", json=payload, timeout=10
            )
            assert response.status_code == 200
            assert response.json()["result"] == expected

        # Clear cache to force re-calculation and DB save
        response = requests.post(f"{self.base_url}/api/cache/clear", timeout=10)
        assert response.status_code == 200

        # Repeat the same operations (should create duplicates in DB)
        for endpoint, payload, expected in workflow_steps_1:
            response = requests.post(
                f"{self.base_url}{endpoint}", json=payload, timeout=10
            )
            assert response.status_code == 200
            assert response.json()["result"] == expected

        # Now check for duplicates
        response = requests.get(f"{self.base_url}/api/database/stats", timeout=10)
        assert response.status_code == 200
        stats = response.json()

        print(f"Database stats after cache clear: {stats}")

        # Should have 3 unique combinations but 6 total operations (duplicates)
        assert stats["unique_combinations"] == 3
        assert stats["duplicates"] == 3  # Now we should have duplicates
        assert stats["total_operations"] == 6

    def test_error_handling_workflow(self):
        """Test error handling in complete workflow"""
        # Step 1: Valid operation
        response = requests.post(f"{self.base_url}/api/pow", json={"x": 2, "y": 3})
        assert response.status_code == 200

        # Step 2: Invalid payload structure
        response = requests.post(f"{self.base_url}/api/pow", json={"invalid": "data"})
        assert response.status_code == 422

        # Step 3: Invalid data types
        response = requests.post(
            f"{self.base_url}/api/factorial", json={"n": "invalid"}
        )
        assert response.status_code == 422

        # Step 4: Negative values where not allowed
        response = requests.post(f"{self.base_url}/api/factorial", json={"n": -1})
        assert response.status_code == 422

        # Step 5: Verify valid operation was still saved
        response = requests.get(f"{self.base_url}/api/requests")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1  # Only the valid operation

    def test_large_dataset_workflow(self):
        """Test workflow with larger dataset"""
        # Generate larger dataset
        operations = []

        # Multiple pow operations
        for x in range(1, 6):
            for y in range(1, 4):
                operations.append(("/api/pow", {"x": x, "y": y}))

        # Multiple factorial operations
        for n in range(1, 8):
            operations.append(("/api/factorial", {"n": n}))

        # Multiple fibonacci operations
        for n in range(1, 11):
            operations.append(("/api/fibonacci", {"n": n}))

        # Execute all operations
        successful_operations = 0
        for endpoint, payload in operations:
            try:
                response = requests.post(
                    f"{self.base_url}{endpoint}", json=payload, timeout=10
                )
                if response.status_code == 200:
                    successful_operations += 1
            except requests.exceptions.RequestException:
                pass  # Some operations might timeout, that's okay for this test

        # Verify a reasonable number succeeded
        assert successful_operations >= len(operations) * 0.8  # At least 80% success

        # Verify database contains operations
        response = requests.get(f"{self.base_url}/api/database/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_operations"] >= successful_operations * 0.8

    def test_cache_clear_workflow(self):
        """Test cache clearing workflow"""
        # Step 1: Perform some operations
        operations = [
            ("/api/pow", {"x": 2, "y": 6}),
            ("/api/factorial", {"n": 8}),
            ("/api/fibonacci", {"n": 15}),
        ]

        for endpoint, payload in operations:
            response = requests.post(f"{self.base_url}{endpoint}", json=payload)
            assert response.status_code == 200

        # Step 2: Verify cache has items
        response = requests.get(f"{self.base_url}/api/cache/stats")
        assert response.status_code == 200
        cache_stats = response.json()
        assert cache_stats["total_cached_operations"] == 3

        # Step 3: Clear cache
        response = requests.post(f"{self.base_url}/api/cache/clear")
        assert response.status_code == 200

        # Step 4: Verify cache is empty
        response = requests.get(f"{self.base_url}/api/cache/stats")
        assert response.status_code == 200
        cache_stats = response.json()
        assert cache_stats["total_cached_operations"] == 0

        # Step 5: Perform same operations again (should recalculate)
        for endpoint, payload in operations:
            response = requests.post(f"{self.base_url}{endpoint}", json=payload)
            assert response.status_code == 200

        # Step 6: Verify database now has duplicates
        response = requests.get(f"{self.base_url}/api/database/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["duplicates"] >= 3  # Should have duplicates now

    def test_concurrent_operations_workflow(self):
        """Test concurrent operations workflow"""
        import statistics
        import time

        print("Testing performance and load workflow...")

        # Test data for performance testing
        performance_operations = [
            ("/api/pow", {"x": 2, "y": 10}, "small power"),
            ("/api/pow", {"x": 5, "y": 15}, "medium power"),
            ("/api/factorial", {"n": 10}, "medium factorial"),
            ("/api/factorial", {"n": 15}, "large factorial"),
            ("/api/fibonacci", {"n": 20}, "medium fibonacci"),
            ("/api/fibonacci", {"n": 25}, "large fibonacci"),
        ]

        print("\n=== Phase 1: Initial Performance Test (Cache Miss) ===")

        initial_times = []
        cache_miss_results = {}

        for endpoint, payload, description in performance_operations:
            print(f"\nTesting {description}: {endpoint} with {payload}")

            start_time = time.time()
            response = requests.post(
                f"{self.base_url}{endpoint}", json=payload, timeout=30
            )
            end_time = time.time()

            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            initial_times.append(response_time)

            assert response.status_code == 200, f"Failed {description}: {response.text}"
            result = response.json()
            cache_miss_results[description] = {
                "result": result["result"],
                "time_ms": response_time,
            }

            print(f"  Result: {result['result']} (Time: {response_time:.2f}ms)")

        print("\nCache Miss Performance Summary:")
        print(f"   Average time: {statistics.mean(initial_times):.2f}ms")
        print(f"   Min time: {min(initial_times):.2f}ms")
        print(f"   Max time: {max(initial_times):.2f}ms")

        print("\n=== Phase 2: Cache Performance Test (Cache Hit) ===")

        cache_hit_times = []

        for endpoint, payload, description in performance_operations:
            print(f"\nTesting cached {description}: {endpoint} with {payload}")

            start_time = time.time()
            response = requests.post(
                f"{self.base_url}{endpoint}", json=payload, timeout=10
            )
            end_time = time.time()

            response_time = (end_time - start_time) * 1000
            cache_hit_times.append(response_time)

            assert response.status_code == 200
            result = response.json()

            # Verify result is identical to cache miss
            expected_result = cache_miss_results[description]["result"]
            assert (
                result["result"] == expected_result
            ), "Cache hit result differs from cache miss"

            print(f"  Cached result: {result['result']} (Time: {response_time:.2f}ms)")

        print("\nCache Hit Performance Summary:")
        print(f"   Average time: {statistics.mean(cache_hit_times):.2f}ms")
        print(f"   Min time: {min(cache_hit_times):.2f}ms")
        print(f"   Max time: {max(cache_hit_times):.2f}ms")

        # Calculate performance improvement
        avg_cache_miss = statistics.mean(initial_times)
        avg_cache_hit = statistics.mean(cache_hit_times)
        speedup = avg_cache_miss / avg_cache_hit if avg_cache_hit > 0 else float("in")

        print(f"\nCache Performance Improvement:")
        print(f"   Speedup: {speedup:.2f}x faster")
        print(f"   Time reduction: {avg_cache_miss - avg_cache_hit:.2f}ms")

        # Assert that cache provides reasonable speedup
        assert (
            speedup >= 2.0
        ), f"Cache should provide at least 2x speedup, got {speedup:.2f}x"

        print("\n=== Phase 3: Concurrent Load Test ===")

        import concurrent.futures
        import threading

        def concurrent_request(request_data):
            """Make a single concurrent request"""
            request_id, endpoint, payload = request_data
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}{endpoint}", json=payload, timeout=15
                )
                end_time = time.time()

                if response.status_code == 200:
                    return {
                        "id": request_id,
                        "success": True,
                        "time_ms": (end_time - start_time) * 1000,
                        "result": response.json()["result"],
                    }
                else:
                    return {
                        "id": request_id,
                        "success": False,
                        "time_ms": (end_time - start_time) * 1000,
                        "error": response.text,
                    }
            except Exception as e:
                return {
                    "id": request_id,
                    "success": False,
                    "time_ms": -1,
                    "error": str(e),
                }

        concurrent_requests = []
        request_id = 0

        # Add some cache hits (repeat previous operations)
        for _ in range(10):
            endpoint, payload, _ = performance_operations[
                request_id % len(performance_operations)
            ]
            concurrent_requests.append((request_id, endpoint, payload))
            request_id += 1

        # Add some new operations (cache misses)
        new_operations = [
            ("/api/pow", {"x": 3, "y": 8}),
            ("/api/pow", {"x": 4, "y": 6}),
            ("/api/factorial", {"n": 12}),
            ("/api/factorial", {"n": 8}),
            ("/api/fibonacci", {"n": 18}),
            ("/api/fibonacci", {"n": 22}),
        ]

        for endpoint, payload in new_operations:
            for _ in range(3):  # Each new operation 3 times
                concurrent_requests.append((request_id, endpoint, payload))
                request_id += 1

        print(f"Executing {len(concurrent_requests)} concurrent requests...")

        # Execute concurrent requests
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(concurrent_request, req) for req in concurrent_requests
            ]
            concurrent_results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]
        end_time = time.time()

        total_test_time = (end_time - start_time) * 1000

        # Analyze concurrent results
        successful_requests = [r for r in concurrent_results if r["success"]]
        failed_requests = [r for r in concurrent_results if not r["success"]]

        if successful_requests:
            response_times = [r["time_ms"] for r in successful_requests]

            print("\nConcurrent Load Test Results:")
            print(f"   Total requests: {len(concurrent_requests)}")
            print(f"   Successful: {len(successful_requests)}")
            print(f"   Failed: {len(failed_requests)}")
            print(
                f"   Success rate: {(len(successful_requests) / len(concurrent_requests) * 100):.1f}%"
            )
            print(f"   Total test time: {total_test_time:.2f}ms")
            print(f"   Average response time: {statistics.mean(response_times):.2f}ms")
            print(f"   Min response time: {min(response_times):.2f}ms")
            print(f"   Max response time: {max(response_times):.2f}ms")
            print(
                f"   Requests per second: {len(successful_requests) / (total_test_time / 1000):.2f}"
            )

        # Print failed requests for debugging
        if failed_requests:
            print("\nFailed Requests:")
            for req in failed_requests[:5]:  # Show first 5 failures
                print(f"   Request {req['id']}: {req['error']}")

        # Assertions for load test
        success_rate = len(successful_requests) / len(concurrent_requests)
        assert (
            success_rate >= 0.9
        ), f"Success rate should be at least 90%, got {success_rate * 100:.1f}%"

        if successful_requests:
            avg_response_time = statistics.mean(response_times)
            assert (
                avg_response_time <= 5000
            ), f"Average response time should be under 5s, got {avg_response_time:.2f}ms"

        print("\n=== Phase 4: Database and Cache State Verification ===")

        # Check final database state
        response = requests.get(f"{self.base_url}/api/database/stats", timeout=10)
        assert response.status_code == 200
        db_stats = response.json()

        print("\nFinal Database State:")
        print(f"   Total operations: {db_stats['total_operations']}")
        print(f"   Unique combinations: {db_stats['unique_combinations']}")
        print(f"   Duplicates: {db_stats['duplicates']}")

        # Check cache state
        response = requests.get(f"{self.base_url}/api/cache/stats", timeout=10)
        assert response.status_code == 200
        cache_stats = response.json()

        print("\nFinal Cache State:")
        print(f"   Cached operations: {cache_stats['total_cached_operations']}")

        # Verify system handled the load properly
        assert db_stats["total_operations"] > 0, "Database should contain operations"
        assert (
            cache_stats["total_cached_operations"] > 0
        ), "Cache should contain operations"

        print("\nPerformance and load test completed successfully!")
        print(f"System handled {len(concurrent_requests)} concurrent requests")
        print(f"Cache provided {speedup:.2f}x performance improvement")
        print(f"{success_rate * 100:.1f}% success rate under load")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short", "-s"])
