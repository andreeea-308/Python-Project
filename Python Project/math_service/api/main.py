import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..db.sqlite_handler import (get_all_operations, get_db_stats,
                                 get_unique_operations, init_db,
                                 save_operation)
from ..exceptions.handlers import handle_generic_exception
from ..models import (FactorialInput, FactorialResult, FibonacciInput,
                      FibonacciResult, PowInput, PowResult)
from ..operations.factorial import factorial
from ..operations.fibonacci import fibonacci
from ..operations.pow import power
from ..utils.cache import (clear_cache, get_cache_stats, get_from_cache,
                           set_in_cache)
from ..utils.logger import get_logger

app = FastAPI(title="Math Operations API", version="1.0.0")
logger = get_logger()

# Serve static HTML frontend

BASE_DIR = Path(__file__).resolve().parent.parent  # ajunge în .../Projects/math_service
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")


def _get_file_response_or_404(file_path: Path, error_message: str):
    """Return FileResponse if file exists, otherwise 404 error."""
    if file_path.exists():
        return FileResponse(str(file_path))
    return {"detail": error_message}


# Rută principală - servește index.html
@app.get("/")
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"detail": "Frontend not found"}


# Rută pentru database.html
@app.get("/database")
def serve_database():
    database_path = FRONTEND_DIR / "database.html"
    if database_path.exists():
        return FileResponse(str(database_path))
    return {"detail": "Database page not found"}


@app.on_event("startup")
def startup():
    init_db()


@app.post("/api/pow", response_model=PowResult)
def calculate_pow(data: PowInput):
    try:
        input_json = data.model_dump_json()
        cached = get_from_cache("pow", input_json)
        if cached:
            logger.info(f"Rezultat din cache pentru pow({data.x}, {data.y})")
            return json.loads(cached)

        result = power(data.x, data.y)
        output = PowResult(x=data.x, y=data.y, result=result)

        result_json = output.model_dump_json()
        set_in_cache("pow", input_json, result_json)
        save_operation("pow", input_json, result_json)

        logger.info(f"Calcul complet pow({data.x}, {data.y}) = {result}")
        return output
    except Exception as e:
        handle_generic_exception(e, context="Eroare API /pow")
        raise HTTPException(status_code=500, detail="Eroare internă")


@app.post("/api/factorial", response_model=FactorialResult)
def calculate_factorial(data: FactorialInput):
    try:
        input_json = data.model_dump_json()
        cached = get_from_cache("factorial", input_json)
        if cached:
            logger.info(f"Rezultat din cache pentru factorial({data.n})")
            return json.loads(cached)

        result = factorial(data.n)
        output = FactorialResult(n=data.n, result=result)

        result_json = output.model_dump_json()
        set_in_cache("factorial", input_json, result_json)
        save_operation("factorial", input_json, result_json)

        logger.info(f"Calcul complet factorial({data.n}) = {result}")
        return output
    except Exception as e:
        handle_generic_exception(e, context="Eroare API /factorial")
        raise HTTPException(status_code=500, detail="Eroare internă")


@app.post("/api/fibonacci", response_model=FibonacciResult)
def calculate_fibonacci(data: FibonacciInput):
    try:
        input_json = data.model_dump_json()
        cached = get_from_cache("fibonacci", input_json)
        if cached:
            logger.info(f"Rezultat din cache pentru fibonacci({data.n})")
            return json.loads(cached)

        result = fibonacci(data.n)
        output = FibonacciResult(n=data.n, result=result)

        result_json = output.model_dump_json()
        set_in_cache("fibonacci", input_json, result_json)
        save_operation("fibonacci", input_json, result_json)

        logger.info(f"Calcul complet fibonacci({data.n}) = {result}")
        return output
    except Exception as e:
        handle_generic_exception(e, context="Eroare API /fibonacci")
        raise HTTPException(status_code=500, detail="Eroare internă")


@app.get("/api/cache/stats")
def get_cache_statistics():
    try:
        return get_cache_stats()
    except Exception as e:
        handle_generic_exception(e, context="Eroare la extragerea statisticilor cache")
        raise HTTPException(status_code=500, detail="Eroare internă")


# Endpoint pentru curățarea cache-ului
@app.post("/api/cache/clear")
def clear_cache_endpoint():
    try:
        clear_cache()
        return {"message": "Cache-ul a fost curățat cu succes"}
    except Exception as e:
        handle_generic_exception(e, context="Eroare la curățarea cache-ului")
        raise HTTPException(status_code=500, detail="Eroare internă")


# Endpoint pentru statistici DB
@app.get("/api/database/stats")
def get_database_statistics():
    try:
        return get_db_stats()
    except Exception as e:
        handle_generic_exception(e, context="Eroare la extragerea statisticilor DB")
        raise HTTPException(status_code=500, detail="Eroare internă")


@app.get("/api/requests")
def get_requests(
    operation_filter: Optional[str] = Query(
        None, description="Filtrează după tipul de operație (pow, fibonacci, factorial)"
    ),
    input_filter: Optional[str] = Query(
        None, description="Filtrează după valoare din input"
    ),
    unique: bool = Query(
        True, description="Returnează doar operațiile unice (implicit True)"
    ),
):
    """
    Returnează operațiile salvate cu opțiuni de filtrare

    Parameters:
    - operation_filter: Filtrează după tipul de operație
    - input_filter: Filtrează după o valoare specifică în input
    - unique: True pentru doar operațiile unice (implicit), False pentru toate
    """
    try:
        if unique:
            # Get unique operations with filters
            data = get_unique_operations(
                operation_filter=operation_filter, input_filter=input_filter
            )
            logger.info(
                f"Returned {len(data)} unique operations with filters: operation={operation_filter}, input={input_filter}"
            )
        else:
            # Get all operations with filters - now this should work
            data = get_all_operations(
                operation_filter=operation_filter, input_filter=input_filter
            )
            logger.info(
                f"Returned {len(data)} operations (all) with filters: operation={operation_filter}, input={input_filter}"
            )

        return {
            "count": len(data),
            "filters": {
                "operation_filter": operation_filter,
                "input_filter": input_filter,
                "unique": unique,
            },
            "data": data,
        }
    except Exception as e:
        handle_generic_exception(e, context="Eroare la extragerea cererilor")
        raise HTTPException(status_code=500, detail="Eroare internă")


# Convenience endpoints for specific filters
@app.get("/api/requests/operation/{operation_type}")
def get_requests_by_operation(operation_type: str):
    """
    Returnează operațiile unice pentru un tip specific de operație
    """
    try:
        data = get_unique_operations(operation_filter=operation_type)
        logger.info(f"Returnat {len(data)} operații unice pentru {operation_type}")
        return {"operation": operation_type, "count": len(data), "data": data}
    except Exception as e:
        handle_generic_exception(
            e, context=f"Eroare la extragerea operațiilor {operation_type}"
        )
        raise HTTPException(status_code=500, detail="Eroare internă")


@app.get("/api/requests/input/{input_value}")
def get_requests_by_input(input_value: str):
    """
    Returnează operațiile unice care conțin o valoare specifică în input
    """
    try:
        data = get_unique_operations(input_filter=input_value)
        logger.info(f"Returnat {len(data)} operații unice cu input-ul '{input_value}'")
        return {"input_filter": input_value, "count": len(data), "data": data}
    except Exception as e:
        handle_generic_exception(
            e, context=f"Eroare la extragerea operațiilor cu input {input_value}"
        )
        raise HTTPException(status_code=500, detail="Eroare internă")


# Example usage endpoints for demonstration
@app.get("/api/examples/unique-operations")
def show_example_usage():
    """
    Endpoint demonstrativ care arată cum să folosești filtrarea
    """
    try:
        examples = {
            "all_unique": {
                "description": "Toate operațiile unice",
                "url": "/api/requests",
                "sample_data": get_unique_operations()[:3],  # First 3 results
            },
            "fibonacci_only": {
                "description": "Doar operațiile fibonacci unice",
                "url": "/api/requests?operation_filter=fibonacci",
                "sample_data": get_unique_operations(operation_filter="fibonacci")[:3],
            },
            "input_with_10": {
                "description": "Operații cu input care conține '10'",
                "url": "/api/requests?input_filter=10",
                "sample_data": get_unique_operations(input_filter="10")[:3],
            },
            "pow_with_2": {
                "description": "Operații pow cu input care conține '2'",
                "url": "/api/requests?operation_filter=pow&input_filter=2",
                "sample_data": get_unique_operations(
                    operation_filter="pow", input_filter="2"
                )[:3],
            },
        }

        return {
            "message": "Exemple de folosire a API-ului de filtrare",
            "examples": examples,
        }
    except Exception as e:
        handle_generic_exception(e, context="Eroare la generarea exemplelor")
        raise HTTPException(status_code=500, detail="Eroare internă")
