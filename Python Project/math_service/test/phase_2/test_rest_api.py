"""
REST API Endpoint Tests
Test Phase 2: REST API Endpoint Testing
"""

import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from math_service.api.main import app
from math_service.utils.cache import clear_cache


class TestRestAPIEndpoints:
    """Test REST API endpoints using TestClient"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Setup test client and clean environment"""
        self.client = TestClient(app)

        # Setup temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        # Copy the structure from the existing operations.db
        self._setup_test_database()

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            clear_cache()
            yield

        # Cleanup
        self._cleanup_database()

    def _setup_test_database(self):
        """Copy database structure from operations.db or create fresh table"""
        operations_db_path = "operations.db"  # Adjust path if needed

        conn = sqlite3.connect(self.temp_db.name)
        try:
            cursor = conn.cursor()

            if os.path.exists(operations_db_path):
                # Get the table schema from existing operations.db
                source_conn = sqlite3.connect(operations_db_path)
                try:
                    source_cursor = source_conn.cursor()
                    source_cursor.execute(
                        "SELECT sql FROM sqlite_master WHERE type='table' AND name='operations'"
                    )
                    table_schema = source_cursor.fetchone()

                    if table_schema:
                        # Execute the CREATE TABLE statement
                        cursor.execute(table_schema[0])
                    else:
                        # Fallback to default schema
                        self._create_default_table(cursor)
                finally:
                    source_conn.close()
            else:
                # Create default table structure
                self._create_default_table(cursor)

            conn.commit()
        finally:
            conn.close()

    def _create_default_table(self, cursor):
        """Create default operations table structure"""
        cursor.execute(
            """
                       CREATE TABLE IF NOT EXISTS operations
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           operation
                           TEXT
                           NOT
                           NULL,
                           input
                           TEXT
                           NOT
                           NULL,
                           result
                           TEXT
                           NOT
                           NULL,
                           timestamp
                           TEXT
                           NOT
                           NULL
                       )
                       """
        )

    def _cleanup_database(self):
        """Properly cleanup the test database"""
        try:
            if hasattr(self, "temp_db") and os.path.exists(self.temp_db.name):
                # Small delay for Windows file handle release
                import time

                time.sleep(0.1)
                os.unlink(self.temp_db.name)
        except (PermissionError, OSError):
            # If we can't delete it, it will be cleaned up by the OS eventually
            pass

    def test_pow_endpoint_valid_input(self):
        """Test /api/pow endpoint with valid input"""
        payload = {"x": 2, "y": 3}

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            response = self.client.post("/api/pow", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["x"] == 2
        assert data["y"] == 3
        assert data["result"] == 8

    def test_pow_endpoint_zero_base(self):
        """Test /api/pow endpoint with zero base"""
        payload = {"x": 0, "y": 5}

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            response = self.client.post("/api/pow", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == 0

    def test_pow_endpoint_negative_values(self):
        """Test /api/pow endpoint with negative values"""
        payload = {"x": -2, "y": 3}

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            response = self.client.post("/api/pow", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == -8

    def test_pow_endpoint_float_values(self):
        """Test /api/pow endpoint with float values"""
        payload = {"x": 2.5, "y": 2}

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            response = self.client.post("/api/pow", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert abs(data["result"] - 6.25) < 0.001

    def test_pow_endpoint_invalid_input(self):
        """Test /api/pow endpoint with invalid input"""
        payload = {"x": "invalid", "y": 3}

        response = self.client.post("/api/pow", json=payload)
        assert response.status_code == 422  # Validation error

    def test_factorial_endpoint_valid_input(self):
        """Test /api/factorial endpoint with valid input"""
        payload = {"n": 5}

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            response = self.client.post("/api/factorial", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["n"] == 5
        assert data["result"] == 120

    def test_factorial_endpoint_zero(self):
        """Test /api/factorial endpoint with zero"""
        payload = {"n": 0}

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            response = self.client.post("/api/factorial", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == 1

    def test_factorial_endpoint_negative_input(self):
        """Test /api/factorial endpoint with negative input"""
        payload = {"n": -1}

        response = self.client.post("/api/factorial", json=payload)
        assert response.status_code == 422  # Validation error due to ge=0 constraint

    def test_factorial_endpoint_large_number(self):
        """Test /api/factorial endpoint with larger number"""
        payload = {"n": 10}

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            response = self.client.post("/api/factorial", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == 3628800

    def test_fibonacci_endpoint_valid_input(self):
        """Test /api/fibonacci endpoint with valid input"""
        payload = {"n": 10}

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            response = self.client.post("/api/fibonacci", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["n"] == 10
        assert data["result"] == 55

    def test_fibonacci_endpoint_base_cases(self):
        """Test /api/fibonacci endpoint with base cases"""
        test_cases = [(0, 0), (1, 1)]

        for n, expected in test_cases:
            payload = {"n": n}

            with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
                response = self.client.post("/api/fibonacci", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["result"] == expected

    def test_fibonacci_endpoint_negative_input(self):
        """Test /api/fibonacci endpoint with negative input"""
        payload = {"n": -1}

        response = self.client.post("/api/fibonacci", json=payload)
        assert response.status_code == 422  # Validation error due to ge=0 constraint

    def test_cache_stats_endpoint(self):
        """Test /api/cache/stats endpoint"""
        response = self.client.get("/api/cache/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_cached_operations" in data
        assert "cached_keys" in data
        assert "cache_size_mb" in data

    def test_cache_clear_endpoint(self):
        """Test /api/cache/clear endpoint"""
        # First add something to cache
        payload = {"x": 2, "y": 3}
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            self.client.post("/api/pow", json=payload)

        # Clear cache
        response = self.client.post("/api/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "succes" in data["message"].lower()

    def test_database_stats_endpoint(self):
        """Test /api/database/stats endpoint"""
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            response = self.client.get("/api/database/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_operations" in data
        assert "unique_combinations" in data
        assert "by_operation" in data

    def test_requests_endpoint_default(self):
        """Test /api/requests endpoint with default parameters"""
        # Add some test data first
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            self.client.post("/api/pow", json={"x": 2, "y": 3})
            self.client.post("/api/factorial", json={"n": 5})

            response = self.client.get("/api/requests")

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "data" in data
        assert "filters" in data

    def test_requests_endpoint_with_filters(self):
        """Test /api/requests endpoint with filters"""
        # Add test data
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            self.client.post("/api/pow", json={"x": 2, "y": 3})
            self.client.post("/api/factorial", json={"n": 5})

            # Test operation filter
            response = self.client.get("/api/requests?operation_filter=pow")
            assert response.status_code == 200
            data = response.json()

            # Should only contain pow operations
            for item in data["data"]:
                assert item["operation"] == "pow"

    def test_requests_by_operation_endpoint(self):
        """Test /api/requests/operation/{operation_type} endpoint"""
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            self.client.post("/api/pow", json={"x": 2, "y": 3})

            response = self.client.get("/api/requests/operation/pow")

        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "pow"
        assert "count" in data
        assert "data" in data

    def test_requests_by_input_endpoint(self):
        """Test /api/requests/input/{input_value} endpoint"""
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            self.client.post("/api/pow", json={"x": 2, "y": 3})

            response = self.client.get("/api/requests/input/2")

        assert response.status_code == 200
        data = response.json()
        assert data["input_filter"] == "2"
        assert "count" in data
        assert "data" in data

    def test_examples_endpoint(self):
        """Test /api/examples/unique-operations endpoint"""
        response = self.client.get("/api/examples/unique-operations")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "examples" in data

    def test_frontend_routes(self):
        """Test frontend routes"""
        # Test main index route
        response = self.client.get("/")
        assert response.status_code == 200

        # Test database route
        response = self.client.get("/database")
        assert response.status_code == 200


class TestAPIValidation:
    """Test API input validation"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Setup test client"""
        self.client = TestClient(app)
        clear_cache()
        yield
        clear_cache()

    def test_pow_missing_fields(self):
        """Test pow endpoint with missing fields"""
        # Missing y field
        response = self.client.post("/api/pow", json={"x": 2})
        assert response.status_code == 422

        # Missing x field
        response = self.client.post("/api/pow", json={"y": 3})
        assert response.status_code == 422

        # Empty payload
        response = self.client.post("/api/pow", json={})
        assert response.status_code == 422

    def test_factorial_invalid_types(self):
        """Test factorial endpoint with invalid types"""
        # String instead of int
        response = self.client.post("/api/factorial", json={"n": "five"})
        assert response.status_code == 422

        # Float instead of int
        response = self.client.post("/api/factorial", json={"n": 5.5})
        assert response.status_code == 422

        # Negative number (violates ge=0 constraint)
        response = self.client.post("/api/factorial", json={"n": -1})
        assert response.status_code == 422

    def test_fibonacci_boundary_validation(self):
        """Test fibonacci endpoint boundary validation"""
        # Negative number (violates ge=0 constraint)
        response = self.client.post("/api/fibonacci", json={"n": -1})
        assert response.status_code == 422

        # Valid boundary case
        response = self.client.post("/api/fibonacci", json={"n": 0})
        assert response.status_code == 200

    def test_invalid_json_format(self):
        """Test endpoints with invalid JSON"""
        # Invalid JSON
        response = self.client.post(
            "/api/pow",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_content_type_validation(self):
        """Test content type validation"""
        # Option 1: Send invalid JSON format
        response = self.client.post("/api/pow", data="invalid json")
        assert response.status_code == 422

        # Option 2: Send form data instead of JSON
        response = self.client.post("/api/pow", data={"x": 2, "y": 3})
        assert response.status_code == 422

        # Option 3: Send XML data with wrong content type
        xml_data = '<?xml version="1.0"?><data><x>2</x><y>3</y></data>'
        response = self.client.post(
            "/api/pow", data=xml_data, headers={"Content-Type": "application/xml"}
        )
        assert response.status_code == 422


class TestAPIPerformance:
    """Test API performance characteristics"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Setup test client"""
        self.client = TestClient(app)

        # Setup temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        # Initialize the database with required table
        self._setup_test_database()

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            clear_cache()
            yield

        # Cleanup
        self._cleanup_database()

    def _setup_test_database(self):
        """Create the operations table in the test database"""
        operations_db_path = "operations.db"  # Adjust path if needed

        conn = sqlite3.connect(self.temp_db.name)
        try:
            cursor = conn.cursor()

            if os.path.exists(operations_db_path):
                # Get the table schema from existing operations.db
                source_conn = sqlite3.connect(operations_db_path)
                try:
                    source_cursor = source_conn.cursor()
                    source_cursor.execute(
                        "SELECT sql FROM sqlite_master WHERE type='table' AND name='operations'"
                    )
                    table_schema = source_cursor.fetchone()

                    if table_schema:
                        # Execute the CREATE TABLE statement
                        cursor.execute(table_schema[0])
                    else:
                        # Fallback to default schema
                        self._create_default_table(cursor)
                finally:
                    source_conn.close()
            else:
                # Create default table structure
                self._create_default_table(cursor)

            conn.commit()
        finally:
            conn.close()

    def _create_default_table(self, cursor):
        """Create default operations table structure"""
        cursor.execute(
            """
                       CREATE TABLE IF NOT EXISTS operations
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           operation
                           TEXT
                           NOT
                           NULL,
                           input
                           TEXT
                           NOT
                           NULL,
                           result
                           TEXT
                           NOT
                           NULL,
                           timestamp
                           TEXT
                           NOT
                           NULL
                       )
                       """
        )

    def _cleanup_database(self):
        """Properly cleanup the test database"""
        try:
            if hasattr(self, "temp_db") and os.path.exists(self.temp_db.name):
                # Small delay for Windows file handle release
                import time

                time.sleep(0.1)
                os.unlink(self.temp_db.name)
        except (PermissionError, OSError):
            # If we can't delete it, it will be cleaned up by the OS eventually
            pass

    def test_api_response_time(self):
        """Test API response times are acceptable"""
        payloads = [
            ("/api/pow", {"x": 2, "y": 10}),
            ("/api/factorial", {"n": 15}),
            ("/api/fibonacci", {"n": 20}),
        ]

        for endpoint, payload in payloads:
            start_time = time.time()

            with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
                response = self.client.post(endpoint, json=payload)

            end_time = time.time()
            response_time = end_time - start_time

            assert (
                response.status_code == 200
            ), f"Failed for {endpoint} with payload {payload}"
            assert (
                response_time < 1.0
            ), f"Response time {response_time:.3f}s too slow for {endpoint}"

            # Optional: Print response times for monitoring
            print(f"{endpoint}: {response_time:.3f}s")

    def test_concurrent_requests_performance(self):
        """Test performance under concurrent load"""
        import queue
        import threading

        def make_request(endpoint, payload, result_queue):
            """Make a request and store the result"""
            start_time = time.time()
            with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
                response = self.client.post(endpoint, json=payload)
            end_time = time.time()

            result_queue.put(
                {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                }
            )

        # Test concurrent requests
        threads = []
        result_queue = queue.Queue()
        payloads = [
            ("/api/pow", {"x": 2, "y": 5}),
            ("/api/factorial", {"n": 10}),
            ("/api/fibonacci", {"n": 15}),
        ]

        # Create and start threads
        for endpoint, payload in payloads * 3:  # 9 concurrent requests
            thread = threading.Thread(
                target=make_request, args=(endpoint, payload, result_queue)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        assert len(results) == 9, "Not all requests completed"

        for result in results:
            assert result["status_code"] == 200, f"Request failed: {result}"
            assert (
                result["response_time"] < 2.0
            ), f"Concurrent request too slow: {result['response_time']:.3f}s"

        # Calculate average response time
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        print(f"Average concurrent response time: {avg_response_time:.3f}s")
        assert (
            avg_response_time < 1.0
        ), f"Average response time too slow: {avg_response_time:.3f}s"


class TestAPIErrorHandling:
    """Test API error handling"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Setup test client"""
        self.client = TestClient(app)
        clear_cache()
        yield
        clear_cache()

    def test_invalid_endpoints(self):
        """Test requests to invalid endpoints"""
        response = self.client.get("/api/nonexistent")
        assert response.status_code == 404

        response = self.client.post("/api/invalid", json={"test": "data"})
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test wrong HTTP methods"""
        # GET on POST endpoint
        response = self.client.get("/api/pow")
        assert response.status_code == 405

        # PUT on POST endpoint
        response = self.client.put("/api/factorial", json={"n": 5})
        assert response.status_code == 405

    def test_large_input_handling(self):
        """Test handling of very large inputs"""
        # Very large numbers that might cause issues
        large_payload = {"x": 10, "y": 100}

        response = self.client.post("/api/pow", json=large_payload)
        # Should either succeed or handle gracefully
        assert response.status_code in [200, 422, 500]

        if response.status_code == 200:
            data = response.json()
            assert "result" in data
            assert isinstance(data["result"], (int, float))


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
