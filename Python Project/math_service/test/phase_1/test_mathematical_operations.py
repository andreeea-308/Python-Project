"""
Unit Tests for Mathematical Operations
Test Phase 1: Unit Testing of Mathematical Operations
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from math_service.operations.factorial import factorial
from math_service.operations.fibonacci import fibonacci
from math_service.operations.pow import power


class TestPowerOperation:
    """Unit tests for power operation"""

    def test_power_positive_integers(self):
        """Test power with positive integers"""
        assert power(2, 3) == 8
        assert power(5, 2) == 25
        assert power(10, 0) == 1

    def test_power_with_zero_base(self):
        """Test power with zero base"""
        assert power(0, 5) == 0
        assert power(0, 0) == 1

    def test_power_with_negative_base(self):
        """Test power with negative base"""
        assert power(-2, 2) == 4
        assert power(-2, 3) == -8
        assert power(-1, 100) == 1

    def test_power_with_negative_exponent(self):
        """Test power with negative exponent"""
        assert power(2, -1) == 0.5
        assert power(4, -2) == 0.0625
        assert power(10, -3) == 0.001

    def test_power_with_float_values(self):
        """Test power with float values"""
        assert abs(power(2.5, 2) - 6.25) < 0.001
        assert abs(power(9, 0.5) - 3) < 0.001
        assert abs(power(1.1, 10) - 2.5937424601) < 0.0001

    def test_power_edge_cases(self):
        """Test power edge cases"""
        assert power(1, 1000000) == 1
        assert power(1000, 0) == 1

    @pytest.mark.parametrize(
        "base,exp,expected",
        [
            (2, 0, 1),
            (2, 1, 2),
            (2, 10, 1024),
            (3, 4, 81),
            (0.5, 2, 0.25),
            (-3, 2, 9),
            (-3, 3, -27),
        ],
    )
    def test_power_parametrized(self, base, exp, expected):
        """Parametrized tests for power operation"""
        result = power(base, exp)
        assert abs(result - expected) < 0.001


class TestFactorialOperation:
    """Unit tests for factorial operation"""

    def test_factorial_small_numbers(self):
        """Test factorial with small numbers"""
        assert factorial(0) == 1
        assert factorial(1) == 1
        assert factorial(2) == 2
        assert factorial(3) == 6
        assert factorial(4) == 24
        assert factorial(5) == 120

    def test_factorial_larger_numbers(self):
        """Test factorial with larger numbers"""
        assert factorial(10) == 3628800
        assert factorial(12) == 479001600

    def test_factorial_negative_number(self):
        """Test factorial with negative number - should raise ValueError"""
        with pytest.raises(
            ValueError, match="Factorial not defined for negative numbers"
        ):
            factorial(-1)

        with pytest.raises(
            ValueError, match="Factorial not defined for negative numbers"
        ):
            factorial(-5)

    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, 1),
            (1, 1),
            (2, 2),
            (3, 6),
            (4, 24),
            (5, 120),
            (6, 720),
            (7, 5040),
            (8, 40320),
            (9, 362880),
            (10, 3628800),
        ],
    )
    def test_factorial_parametrized(self, n, expected):
        """Parametrized tests for factorial operation"""
        assert factorial(n) == expected

    def test_factorial_performance(self):
        """Test factorial performance with reasonable large numbers"""
        import time

        start_time = time.time()
        result = factorial(20)
        end_time = time.time()

        assert result == 2432902008176640000
        assert (end_time - start_time) < 0.1  # Should complete in less than 0.1 seconds


class TestFibonacciOperation:
    """Unit tests for fibonacci operation"""

    def test_fibonacci_base_cases(self):
        """Test fibonacci base cases"""
        assert fibonacci(0) == 0
        assert fibonacci(1) == 1

    def test_fibonacci_small_numbers(self):
        """Test fibonacci with small numbers"""
        assert fibonacci(2) == 1
        assert fibonacci(3) == 2
        assert fibonacci(4) == 3
        assert fibonacci(5) == 5
        assert fibonacci(6) == 8
        assert fibonacci(7) == 13
        assert fibonacci(8) == 21

    def test_fibonacci_larger_numbers(self):
        """Test fibonacci with larger numbers"""
        assert fibonacci(10) == 55
        assert fibonacci(15) == 610
        assert fibonacci(20) == 6765

    def test_fibonacci_negative_number(self):
        """Test fibonacci with negative number - should raise ValueError"""
        with pytest.raises(
            ValueError, match="Fibonacci not defined for negative numbers"
        ):
            fibonacci(-1)

        with pytest.raises(
            ValueError, match="Fibonacci not defined for negative numbers"
        ):
            fibonacci(-10)

    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, 0),
            (1, 1),
            (2, 1),
            (3, 2),
            (4, 3),
            (5, 5),
            (6, 8),
            (7, 13),
            (8, 21),
            (9, 34),
            (10, 55),
            (11, 89),
            (12, 144),
            (13, 233),
            (14, 377),
            (15, 610),
        ],
    )
    def test_fibonacci_parametrized(self, n, expected):
        """Parametrized tests for fibonacci operation"""
        assert fibonacci(n) == expected

    def test_fibonacci_sequence_property(self):
        """Test fibonacci sequence property: F(n) = F(n-1) + F(n-2)"""
        for n in range(2, 20):
            assert fibonacci(n) == fibonacci(n - 1) + fibonacci(n - 2)

    def test_fibonacci_performance(self):
        """Test fibonacci performance"""
        import time

        start_time = time.time()
        result = fibonacci(30)
        end_time = time.time()

        assert result == 832040
        assert (end_time - start_time) < 0.1  # Should complete in less than 0.1 seconds


class TestMathematicalOperationsIntegration:
    """Integration tests for mathematical operations"""

    def test_operations_with_same_input(self):
        """Test different operations with same input where applicable"""
        # Test with n=5
        pow_result = power(5, 2)  # 5^2 = 25
        fact_result = factorial(5)  # 5! = 120
        fib_result = fibonacci(5)  # F(5) = 5

        assert pow_result == 25
        assert fact_result == 120
        assert fib_result == 5

    def test_operations_consistency(self):
        """Test operations return consistent results"""
        # Multiple calls should return same results
        for _ in range(5):
            assert power(3, 4) == 81
            assert factorial(6) == 720
            assert fibonacci(10) == 55

    def test_operations_type_consistency(self):
        """Test operations return correct types"""
        pow_result = power(2, 3)
        fact_result = factorial(5)
        fib_result = fibonacci(8)

        assert isinstance(pow_result, (int, float))
        assert isinstance(fact_result, int)
        assert isinstance(fib_result, int)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
