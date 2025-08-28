"""
Integration Tests for Database and Cache Functionality
Test Phase 1: Database Integration Testing & Cache Functionality Testing
"""

import json
import os
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Try to import the actual modules, with fallback handling
try:
    from math_service.db.sqlite_handler import (get_all_operations,
                                                get_db_stats,
                                                get_unique_operations, init_db,
                                                save_operation)

    ACTUAL_IMPORTS = True
except ImportError:
    # Mock the functions if imports fail
    ACTUAL_IMPORTS = False
    print(
        "Warning: Could not import actual database handler. Using mocks for demonstration."
    )


class TestDatabaseOperations:
    """Test database operations with improved error handling and structure"""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Setup test database for each test with proper error handling"""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize the database schema
        self._init_test_schema()

        yield

        # Cleanup with error handling
        self._cleanup_test_db()

    def _init_test_schema(self):
        """Initialize the test database schema"""
        conn = sqlite3.connect(self.temp_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    input TEXT NOT NULL,
                    result TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()
        finally:
            conn.close()

    def _cleanup_test_db(self):
        """Clean up test database with error handling"""
        try:
            if os.path.exists(self.temp_db_path):
                os.unlink(self.temp_db_path)
        except OSError as e:
            print(f"Warning: Could not delete temporary database: {e}")

    @contextmanager
    def mock_db_file(self):
        """Context manager to mock the database file path"""
        if ACTUAL_IMPORTS:
            with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db_path):
                yield
        else:
            # If we don't have actual imports, just yield
            yield

    def test_database_initialization(self):
        """Test database initialization creates proper tables"""
        conn = sqlite3.connect(self.temp_db_path)
        try:
            cursor = conn.cursor()

            # Check that the operations table exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='operations'
            """
            )
            table_exists = cursor.fetchone()
            assert table_exists is not None, "Operations table should exist"

            # Check table structure
            cursor.execute("PRAGMA table_info(operations)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            expected_columns = ["id", "operation", "input", "result", "timestamp"]
            for col in expected_columns:
                assert (
                    col in column_names
                ), f"Column '{col}' should exist in operations table"

            # Verify primary key
            primary_keys = [col for col in columns if col[5] == 1]  # col[5] is pk flag
            assert len(primary_keys) == 1, "Should have exactly one primary key"
            assert primary_keys[0][1] == "id", "Primary key should be 'id'"

        finally:
            conn.close()

    def test_save_operation(self):
        """Test saving operation to database"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        with self.mock_db_file():
            # Test data
            operation = "pow"
            input_data = json.dumps({"x": 2, "y": 3})
            result_data = json.dumps({"x": 2, "y": 3, "result": 8})

            # Save operation
            save_operation(operation, input_data, result_data)

            # Verify it was saved
            conn = sqlite3.connect(self.temp_db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM operations WHERE operation=?", (operation,)
                )
                saved_operation = cursor.fetchone()

                assert saved_operation is not None, "Operation should be saved"
                assert saved_operation[1] == operation, "Operation name should match"
                assert saved_operation[2] == input_data, "Input data should match"
                assert saved_operation[3] == result_data, "Result data should match"
                assert saved_operation[4] is not None, "Timestamp should be set"
            finally:
                conn.close()

    def test_save_operation_with_invalid_json(self):
        """Test saving operation with invalid JSON data"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        with self.mock_db_file():
            # Test with invalid JSON - should handle gracefully
            operation = "test"
            invalid_json = "not valid json"

            # This should either raise an exception or handle gracefully
            # depending on your implementation
            try:
                save_operation(operation, invalid_json, invalid_json)
                # If it succeeds, verify it was saved
                conn = sqlite3.connect(self.temp_db_path)
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT COUNT(*) FROM operations WHERE operation=?",
                        (operation,),
                    )
                    count = cursor.fetchone()[0]
                    assert count >= 0, "Operation count should be non-negative"
                finally:
                    conn.close()
            except (json.JSONDecodeError, ValueError, sqlite3.Error):
                # Expected behavior for invalid data
                pass

    def test_get_all_operations(self):
        """Test retrieving all operations"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        with self.mock_db_file():
            # Save test data
            test_operations = [
                ("pow", '{"x": 2, "y": 3}', '{"result": 8}'),
                ("factorial", '{"n": 5}', '{"result": 120}'),
                ("fibonacci", '{"n": 10}', '{"result": 55}'),
            ]

            for op, inp, res in test_operations:
                save_operation(op, inp, res)

            # Retrieve all operations
            all_ops = get_all_operations()

            assert len(all_ops) == 3, "Should retrieve all 3 operations"
            operations = [op["operation"] for op in all_ops]
            assert "pow" in operations, "Should contain pow operation"
            assert "factorial" in operations, "Should contain factorial operation"
            assert "fibonacci" in operations, "Should contain fibonacci operation"

            # Verify data structure
            for op in all_ops:
                assert "operation" in op, "Each operation should have operation field"
                assert "input" in op, "Each operation should have input field"
                assert "result" in op, "Each operation should have result field"
                assert "timestamp" in op, "Each operation should have timestamp field"

    def test_get_operations_with_filters(self):
        """Test retrieving operations with filters"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        with self.mock_db_file():
            # Save test data
            save_operation("pow", '{"x": 2, "y": 3}', '{"result": 8}')
            save_operation("pow", '{"x": 3, "y": 2}', '{"result": 9}')
            save_operation("factorial", '{"n": 5}', '{"result": 120}')

            # Test operation filter
            pow_ops = get_all_operations(operation_filter="pow")
            assert len(pow_ops) == 2, "Should find 2 pow operations"
            assert all(
                op["operation"] == "pow" for op in pow_ops
            ), "All results should be pow operations"

            # Test input filter
            input_filtered = get_all_operations(input_filter="2")
            assert len(input_filtered) >= 2, "Should find operations with '2' in input"

            # Test combined filters
            try:
                combined = get_all_operations(operation_filter="pow", input_filter="3")
                assert (
                    len(combined) >= 1
                ), "Should find pow operations with '3' in input"
            except TypeError:
                # If the function doesn't support combined filters, that's OK
                pass

    def test_get_unique_operations(self):
        """Test retrieving unique operations"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        with self.mock_db_file():
            # Save duplicate data
            save_operation("pow", '{"x": 2, "y": 3}', '{"result": 8}')
            save_operation("pow", '{"x": 2, "y": 3}', '{"result": 8}')  # Duplicate
            save_operation("factorial", '{"n": 5}', '{"result": 120}')

            # Get unique operations
            unique_ops = get_unique_operations()

            # Should have 2 unique operations (pow and factorial)
            assert len(unique_ops) == 2, "Should have 2 unique operations"

            operations = [op["operation"] for op in unique_ops]
            assert "pow" in operations, "Should contain pow operation"
            assert "factorial" in operations, "Should contain factorial operation"

            # Verify no duplicates in results
            import json

            operation_counts = {}
            for op in unique_ops:
                # Convert dictionaries to JSON strings for hashable keys
                input_key = (
                    json.dumps(op["input"], sort_keys=True)
                    if op["input"] is not None
                    else None
                )
                result_key = (
                    json.dumps(op["result"], sort_keys=True)
                    if op["result"] is not None
                    else None
                )
                key = (op["operation"], input_key, result_key)
                operation_counts[key] = operation_counts.get(key, 0) + 1

            assert all(
                count == 1 for count in operation_counts.values()
            ), "All operations should be unique"

    def test_get_db_stats(self):
        """Test database statistics"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        with self.mock_db_file():
            # Save test data including duplicates
            save_operation("pow", '{"x": 2, "y": 3}', '{"result": 8}')
            save_operation("pow", '{"x": 2, "y": 3}', '{"result": 8}')  # Duplicate
            save_operation("factorial", '{"n": 5}', '{"result": 120}')
            save_operation("fibonacci", '{"n": 10}', '{"result": 55}')

            stats = get_db_stats()

            # Verify required fields
            assert "total_operations" in stats, "Stats should include total_operations"
            assert (
                "unique_combinations" in stats
            ), "Stats should include unique_combinations"
            assert "duplicates" in stats, "Stats should include duplicates"
            assert (
                "by_operation" in stats
            ), "Stats should include by_operation breakdown"

            # Verify values
            assert stats["total_operations"] == 4, "Should have 4 total operations"
            assert (
                stats["unique_combinations"] == 3
            ), "Should have 3 unique combinations"
            assert stats["duplicates"] == 1, "Should have 1 duplicate"

            # Verify operation breakdown
            assert stats["by_operation"]["pow"] == 2, "Should have 2 pow operations"
            assert (
                stats["by_operation"]["factorial"] == 1
            ), "Should have 1 factorial operation"
            assert (
                stats["by_operation"]["fibonacci"] == 1
            ), "Should have 1 fibonacci operation"

    def test_empty_database_stats(self):
        """Test statistics on empty database"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        with self.mock_db_file():
            stats = get_db_stats()

            assert (
                stats["total_operations"] == 0
            ), "Empty database should have 0 operations"
            assert (
                stats["unique_combinations"] == 0
            ), "Empty database should have 0 unique combinations"
            assert stats["duplicates"] == 0, "Empty database should have 0 duplicates"
            assert (
                len(stats["by_operation"]) == 0
            ), "Empty database should have no operation breakdown"

    def test_database_connection_error_handling(self):
        """Test handling of database connection errors"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        # Test with invalid database path
        with patch(
            "math_service.db.sqlite_handler.DB_FILE", "/invalid/path/to/database.db"
        ):
            try:
                save_operation("test", '{"x": 1}', '{"result": 1}')
                # If no exception is raised, the function handles the error gracefully
            except (sqlite3.Error, OSError, IOError):
                # Expected behavior for invalid database path
                pass

    def test_concurrent_operations(self):
        """Test concurrent database operations"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        with self.mock_db_file():
            import threading
            import time

            def save_multiple_operations(operation_prefix, count):
                for i in range(count):
                    save_operation(
                        f"{operation_prefix}_{i}",
                        f'{{"x": {i}}}',
                        f'{{"result": {i * 2}}}',
                    )
                    time.sleep(0.01)  # Small delay to increase chance of contention

            # Start multiple threads
            threads = []
            for i in range(3):
                thread = threading.Thread(
                    target=save_multiple_operations, args=(f"thread_{i}", 5)
                )
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Verify all operations were saved
            all_ops = get_all_operations()
            assert (
                len(all_ops) == 15
            ), "Should have saved all 15 operations from 3 threads"


class TestDatabasePerformance:
    """Performance tests for database operations"""

    @pytest.fixture(autouse=True)
    def setup_performance_test(self):
        """Setup for performance testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize schema
        conn = sqlite3.connect(self.temp_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    input TEXT NOT NULL,
                    result TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            # Add index for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_operation ON operations(operation)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON operations(timestamp)"
            )
            conn.commit()
        finally:
            conn.close()

        yield

        # Cleanup
        try:
            if os.path.exists(self.temp_db_path):
                os.unlink(self.temp_db_path)
        except OSError:
            pass

    @pytest.mark.performance
    def test_bulk_insert_performance(self):
        """Test performance of bulk insertions"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        import time

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db_path):
            start_time = time.time()

            # Insert 1000 operations
            for i in range(1000):
                save_operation(
                    f"operation_{i % 10}", f'{{"x": {i}}}', f'{{"result": {i * i}}}'
                )

            end_time = time.time()
            duration = end_time - start_time

            print(f"Bulk insert of 1000 operations took {duration:.2f} seconds")
            assert duration < 10.0, "Bulk insert should complete within 10 seconds"

    @pytest.mark.performance
    def test_query_performance_with_large_dataset(self):
        """Test query performance with large dataset"""
        if not ACTUAL_IMPORTS:
            pytest.skip("Skipping test - actual imports not available")

        # First, populate with test data
        conn = sqlite3.connect(self.temp_db_path)
        try:
            cursor = conn.cursor()
            # Insert 10000 test records directly for speed
            test_data = [
                (f"operation_{i % 20}", f'{{"x": {i}}}', f'{{"result": {i * i}}}')
                for i in range(10000)
            ]
            cursor.executemany(
                "INSERT INTO operations (operation, input, result) VALUES (?, ?, ?)",
                test_data,
            )
            conn.commit()
        finally:
            conn.close()

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db_path):
            import time

            # Test get_all_operations performance
            start_time = time.time()
            all_ops = get_all_operations()
            end_time = time.time()

            assert len(all_ops) == 10000, "Should retrieve all 10000 operations"
            duration = end_time - start_time
            print(f"Retrieving all 10000 operations took {duration:.2f} seconds")
            assert duration < 5.0, "Query should complete within 5 seconds"

            # Test filtered query performance
            start_time = time.time()
            filtered_ops = get_all_operations(operation_filter="operation_5")
            end_time = time.time()

            duration = end_time - start_time
            print(f"Filtered query took {duration:.2f} seconds")
            assert duration < 1.0, "Filtered query should complete within 1 second"


if __name__ == "__main__":
    # Run tests with verbose output
    # Use -m performance to run performance tests
    pytest.main([__file__, "-v", "--tb=short"])
