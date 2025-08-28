"""
Integration Tests for Database and Cache Functionality
Test Phase 1: Database Integration Testing & Cache Functionality Testing
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from math_service.db.sqlite_handler import (get_all_operations, get_db_stats,
                                            init_db, save_operation)
from math_service.utils.cache import (clear_cache, get_cache, get_cache_stats,
                                      get_from_cache, memory_cache,
                                      set_in_cache)


class TestCacheOperations:
    """Test cache operations"""

    @pytest.fixture(autouse=True)
    def setup_cache(self):
        """Clear cache before each test"""
        clear_cache()
        yield
        clear_cache()

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        operation = "pow"
        input_data = '{"x": 2, "y": 3}'
        result_data = '{"result": 8}'

        # Initially should be empty
        cached = get_from_cache(operation, input_data)
        assert cached is None

        # Set in cache
        set_in_cache(operation, input_data, result_data)

        # Should now be in cache
        cached = get_from_cache(operation, input_data)
        assert cached == result_data

    def test_cache_miss(self):
        """Test cache miss scenario"""
        result = get_from_cache("pow", '{"x": 999, "y": 999}')
        assert result is None

    def test_cache_different_operations(self):
        """Test cache with different operations"""
        # Cache different operations
        set_in_cache("pow", '{"x": 2, "y": 3}', '{"result": 8}')
        set_in_cache("factorial", '{"n": 5}', '{"result": 120}')
        set_in_cache("fibonacci", '{"n": 10}', '{"result": 55}')

        # Verify all are cached correctly
        assert get_from_cache("pow", '{"x": 2, "y": 3}') == '{"result": 8}'
        assert get_from_cache("factorial", '{"n": 5}') == '{"result": 120}'
        assert get_from_cache("fibonacci", '{"n": 10}') == '{"result": 55}'

    def test_cache_stats(self):
        """Test cache statistics"""
        # Initially empty
        stats = get_cache_stats()
        assert stats["total_cached_operations"] == 0
        assert stats["cached_keys"] == []

        # Add some cached items
        set_in_cache("pow", '{"x": 2, "y": 3}', '{"result": 8}')
        set_in_cache("factorial", '{"n": 5}', '{"result": 120}')

        stats = get_cache_stats()
        assert stats["total_cached_operations"] == 2
        assert len(stats["cached_keys"]) == 2
        assert 'pow({"x": 2, "y": 3})' in stats["cached_keys"]
        assert 'factorial({"n": 5})' in stats["cached_keys"]

    def test_clear_cache(self):
        """Test cache clearing"""
        # Add items to cache
        set_in_cache("pow", '{"x": 2, "y": 3}', '{"result": 8}')
        set_in_cache("factorial", '{"n": 5}', '{"result": 120}')

        # Verify cache has items
        cache = get_cache()
        assert len(cache) == 2

        # Clear cache
        clear_cache()

        # Verify cache is empty
        cache = get_cache()
        assert len(cache) == 0

    def test_cache_key_uniqueness(self):
        """Test that cache keys are unique per operation and input"""
        # Same operation, different inputs
        set_in_cache("pow", '{"x": 2, "y": 3}', '{"result": 8}')
        set_in_cache("pow", '{"x": 3, "y": 2}', '{"result": 9}')

        # Different operation, same input structure
        set_in_cache("factorial", '{"n": 5}', '{"result": 120}')

        assert get_from_cache("pow", '{"x": 2, "y": 3}') == '{"result": 8}'
        assert get_from_cache("pow", '{"x": 3, "y": 2}') == '{"result": 9}'
        assert get_from_cache("factorial", '{"n": 5}') == '{"result": 120}'

        # Wrong combination should return None
        assert get_from_cache("factorial", '{"x": 2, "y": 3}') is None


class TestDatabaseCacheIntegration:
    """Test integration between database and cache"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment"""
        # Setup test database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            init_db()
            clear_cache()
            yield

        # Cleanup
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        clear_cache()

    def test_cache_prevents_duplicate_db_saves(self):
        """Test that cache prevents duplicate database saves"""
        # Use the correct module path for patching
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            operation = "pow"
            input_data = '{"x": 2, "y": 3}'
            result_data = '{"result": 8}'

            # First save - should go to both cache and DB
            save_operation(operation, input_data, result_data)
            set_in_cache(operation, input_data, result_data)

            # Check DB has one entry
            all_ops = get_all_operations()
            assert len(all_ops) == 1

            # Cache hit should prevent another DB save
            cached_result = get_from_cache(operation, input_data)
            assert cached_result == result_data

            # DB should still have only one entry
            all_ops = get_all_operations()
            assert len(all_ops) == 1

    def test_cache_and_db_consistency(self):
        """Test consistency between cache and database"""
        with patch("math_service.db.sqlite_handler.DB_FILE", self.temp_db.name):
            test_data = [
                ("pow", '{"x": 2, "y": 3}', '{"result": 8}'),
                ("factorial", '{"n": 5}', '{"result": 120}'),
                ("fibonacci", '{"n": 10}', '{"result": 55}'),
            ]

            # Save to both cache and DB
            for op, inp, res in test_data:
                save_operation(op, inp, res)
                set_in_cache(op, inp, res)

            # Verify cache and DB have same data
            cache_stats = get_cache_stats()
            db_stats = get_db_stats()

            assert cache_stats["total_cached_operations"] == 3
            assert db_stats["total_operations"] == 3

            # Verify specific entries match
            for op, inp, res in test_data:
                cached_result = get_from_cache(op, inp)
                assert cached_result == res

            # Verify DB contains all operations
            all_db_ops = get_all_operations()
            assert len(all_db_ops) == 3

            db_operations = [op["operation"] for op in all_db_ops]
            assert "pow" in db_operations
            assert "factorial" in db_operations
            assert "fibonacci" in db_operations


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
