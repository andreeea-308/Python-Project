from pydantic import BaseModel, Field


class PowInput(BaseModel):
    x: float = Field(..., description="Baza")
    y: float = Field(..., description="Exponentul")


class PowResult(BaseModel):
    operation: str = "pow"
    x: float
    y: float
    result: float


class FibonacciInput(BaseModel):
    n: int = Field(..., ge=0, description="Pozitia in sir")


class FibonacciResult(BaseModel):
    operation: str = "fibonacci"
    n: int
    result: int


class FactorialInput(BaseModel):
    n: int = Field(..., ge=0, description="Număr pentru factorial")


class FactorialResult(BaseModel):
    operation: str = "factorial"
    n: int
    result: int
