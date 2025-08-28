import sys
from pathlib import Path

import click
from pydantic_core._pydantic_core import ValidationError

sys.path.append(str(Path(__file__).parent))
from queue import Queue

from db.sqlite_handler import init_db, save_operation
from exceptions.handlers import (handle_generic_exception,
                                 handle_validation_error)
from models import (FactorialInput, FactorialResult, FibonacciInput,
                    FibonacciResult, PowInput, PowResult)
from operations.factorial import factorial as factorial_fn
from operations.fibonacci import fibonacci as fibonacci_fn
from operations.pow import power
from utils.cache import get_from_cache, set_in_cache
from utils.logger import get_logger
from workers.thread_worker import MathWorker

task_queue = Queue()
worker = MathWorker(task_queue)
worker.start()
logger = get_logger()


@click.group()
def cli():
    """Interfață de comandă pentru operații matematice"""
    init_db()  # ne asigurăm că baza e creată
    pass


@cli.command()
@click.option("--x", type=float, required=True, help="Baza")
@click.option("--y", type=float, required=True, help="Exponentul")
def pow(x, y):
    """Calculează x la puterea y în worker"""

    try:
        data = PowInput(x=x, y=y)
    except Exception as e:
        handle_validation_error(e)
        return

    input_json = data.model_dump_json()
    cached = get_from_cache("pow", input_json)
    if cached:
        logger.info(f"Rezultat din cache pentru {x}^{y}")
        click.echo(cached)
        return

    def on_result(result: float):
        output = PowResult(x=data.x, y=data.y, result=result)
        result_json = output.model_dump_json()
        set_in_cache("pow", input_json, result_json)
        save_operation("pow", input_json, result_json)
        logger.info(f" {x}^{y} = {result}")
        click.echo(result_json)

    logger.debug(f"➡Trimit către worker: pow({x}, {y})")
    task_queue.put(
        {"func": power, "args": {"x": data.x, "y": data.y}, "callback": on_result}
    )
    task_queue.join()


@cli.command()  # Changed from @click.command() to @cli.command()
@click.option("--n", type=int, required=True, help="Pozitia in sirul Fibonacci")
def fibonacci(n):
    """Calculează al n-lea număr Fibonacci în worker thread"""

    try:
        data = FibonacciInput(n=n)
    except ValidationError as e:
        handle_validation_error(e)
        return
    except Exception as e:
        handle_generic_exception(e, context="Eroare la validarea FibonacciInput")
        return

    input_json = data.model_dump_json()
    cached = get_from_cache("fibonacci", input_json)
    if cached:
        logger.info(f"Rezultat din cache pentru n={n}")
        click.echo(cached)
        return

    def on_result(result: int):
        output = FibonacciResult(n=data.n, result=result)
        result_json = output.model_dump_json()

        set_in_cache("fibonacci", input_json, result_json)
        save_operation("fibonacci", input_json, result_json)

        logger.info(f"Fibonacci({n}) calculat de worker: {result}")
        click.echo(result_json)

    logger.debug(f"Trimit către worker: fibonacci({n})")
    task_queue.put({"func": fibonacci_fn, "args": {"n": data.n}, "callback": on_result})
    task_queue.join()


@cli.command()
@click.option("--n", type=int, required=True, help="Număr pentru factorial")
def factorial(n):
    """Calculează factorialul unui număr în worker"""

    try:
        data = FactorialInput(n=n)
    except Exception as e:
        handle_validation_error(e)
        return

    input_json = data.model_dump_json()
    cached = get_from_cache("factorial", input_json)
    if cached:
        logger.info(f"Rezultat din cache pentru factorial({n})")
        click.echo(cached)
        return

    def on_result(result: int):
        output = FactorialResult(n=data.n, result=result)
        result_json = output.model_dump_json()
        set_in_cache("factorial", input_json, result_json)
        save_operation("factorial", input_json, result_json)
        logger.info(f"factorial({n}) = {result}")
        click.echo(result_json)

    logger.debug(f"Trimit către worker: factorial({n})")
    task_queue.put({"func": factorial_fn, "args": {"n": data.n}, "callback": on_result})
    task_queue.join()


if __name__ == "__main__":
    cli()
