import logging

import click
from pydantic import ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_validation_error(error: ValidationError):
    logger.error(f"Input invalid: {error}")
    click.echo(f"Input invalid: {error}")


def handle_generic_exception(error: Exception, context: str = "Eroare"):
    logger.exception(f"{context}: {error}")
    click.echo(f" {context}: {error}")
