def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("Fibonacci not defined for negative numbers")
    if n in (0, 1):
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b
