import json

import click
import requests

API_BASE = "http://localhost:8000/api"


@click.group()
def cli():
    """CLI client pentru REST API-ul Math Service"""
    pass


@cli.command()
@click.option("--x", type=float, required=True, help="Baza")
@click.option("--y", type=float, required=True, help="Exponentul")
def pow(x, y):
    """Client REST pentru pow(x, y)"""
    payload = {"x": x, "y": y}
    try:
        response = requests.post(f"{API_BASE}/pow", json=payload)
        response.raise_for_status()
        click.echo(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        click.echo(f"Eroare: {e}", err=True)


@cli.command()
@click.option("--n", type=int, required=True, help="Pozitia în șirul Fibonacci")
def fibonacci(n):
    """Client REST pentru fibonacci(n)"""
    payload = {"n": n}
    try:
        response = requests.post(f"{API_BASE}/fibonacci", json=payload)
        response.raise_for_status()
        click.echo(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        click.echo(f"Eroare: {e}", err=True)


@click.option(
    "--operation-filter",
    type=click.Choice(["pow", "fibonacci", "factorial"]),
    help="Filtrează după tipul de operație",
)
@click.option("--input-filter", help="Filtrează după valoare din input")
@click.option(
    "--unique/--all",
    default=True,
    help="Afișează doar operațiile unice (implicit) sau toate",
)
@click.option("--limit", type=int, help="Limitează numărul de rezultate afișate")
def history(operation_filter, input_filter, unique, limit):
    """Afișează cererile persistate în SQLite cu opțiuni de filtrare"""
    try:
        params = {}
        if operation_filter:
            params["operation_filter"] = operation_filter
        if input_filter:
            params["input_filter"] = input_filter
        params["unique"] = unique

        response = requests.get(f"{API_BASE}/requests", params=params)
        response.raise_for_status()
        result = response.json()

        data = result.get("data", [])
        count = result.get("count", 0)
        filters = result.get("filters", {})

        if not data:
            click.echo("Nu au fost găsite înregistrări cu filtrele specificate.")
            return

        # Aplicăm limita dacă este specificată
        if limit:
            data = data[:limit]
            click.echo(f"Afișez primele {len(data)} din {count} înregistrări găsite.")
        else:
            click.echo(f"Găsite {count} înregistrări.")

        # Afișăm filtrele active
        active_filters = []
        if filters.get("operation_filter"):
            active_filters.append(f"Operație: {filters['operation_filter']}")
        if filters.get("input_filter"):
            active_filters.append(f"Input: {filters['input_filter']}")
        if filters.get("unique"):
            active_filters.append("Doar unice")

        if active_filters:
            click.echo(f"Filtre active: {', '.join(active_filters)}")

        click.echo("-" * 60)

        for i, item in enumerate(data, 1):
            click.echo(f"{i}. Operația: {item.get('operation', 'N/A')}")
            click.echo(f"   Input: {item.get('input', 'N/A')}")
            click.echo(f"   Rezultat: {item.get('result', 'N/A')}")
            click.echo(f"   Timestamp: {item.get('timestamp', 'N/A')}")
            click.echo("-" * 30)

    except requests.exceptions.RequestException as e:
        click.echo(f"Eroare la accesarea istoricului: {e}", err=True)


# Comenzi specifice pentru filtrare rapidă
@cli.command()
@click.argument("operation_type", type=click.Choice(["pow", "fibonacci", "factorial"]))
@click.option(
    "--limit", type=int, default=10, help="Numărul de rezultate (implicit 10)"
)
def show_operation(operation_type, limit):
    """Afișează operațiile unice pentru un tip specific"""
    try:
        response = requests.get(f"{API_BASE}/requests/operation/{operation_type}")
        response.raise_for_status()
        result = response.json()

        data = result.get("data", [])
        count = result.get("count", 0)

        if not data:
            click.echo(f"Nu au fost găsite operații de tipul '{operation_type}'.")
            return

        click.echo(f"Găsite {count} operații unice de tipul '{operation_type}':")
        click.echo("=" * 50)

        for i, item in enumerate(data[:limit], 1):
            click.echo(f"{i}. Input: {item.get('input', 'N/A')}")
            click.echo(f"   Rezultat: {item.get('result', 'N/A')}")
            click.echo(f"   Timestamp: {item.get('timestamp', 'N/A')}")
            if i < len(data[:limit]):
                click.echo()

        if len(data) > limit:
            click.echo(
                f"... și încă {len(data) - limit} rezultate. Folosește --limit pentru a vedea mai multe."
            )

    except requests.exceptions.RequestException as e:
        click.echo(f"Eroare: {e}", err=True)


@cli.command()
@click.argument("input_value")
@click.option(
    "--limit", type=int, default=10, help="Numărul de rezultate (implicit 10)"
)
def show_input(input_value, limit):
    """Afișează operațiile care conțin o valoare specifică în input"""
    try:
        response = requests.get(f"{API_BASE}/requests/input/{input_value}")
        response.raise_for_status()
        result = response.json()

        data = result.get("data", [])
        count = result.get("count", 0)

        if not data:
            click.echo(
                f"Nu au fost găsite operații cu input-ul care conține '{input_value}'."
            )
            return

        click.echo(f"Găsite {count} operații cu input-ul care conține '{input_value}':")
        click.echo("=" * 50)

        for i, item in enumerate(data[:limit], 1):
            click.echo(f"{i}. Operația: {item.get('operation', 'N/A')}")
            click.echo(f"   Input: {item.get('input', 'N/A')}")
            click.echo(f"   Rezultat: {item.get('result', 'N/A')}")
            click.echo(f"   Timestamp: {item.get('timestamp', 'N/A')}")
            if i < len(data[:limit]):
                click.echo()

        if len(data) > limit:
            click.echo(
                f"... și încă {len(data) - limit} rezultate. Folosește --limit pentru a vedea mai multe."
            )

    except requests.exceptions.RequestException as e:
        click.echo(f"Eroare: {e}", err=True)


@cli.command()
def examples():
    """Afișează exemple de folosire a filtrării"""
    try:
        response = requests.get(f"{API_BASE}/examples/unique-operations")
        response.raise_for_status()
        result = response.json()

        click.echo("EXEMPLE DE FOLOSIRE A FILTRĂRII")
        click.echo("=" * 50)

        examples = result.get("examples", {})
        for key, example in examples.items():
            click.echo(f"\n{example['description']}:")
            click.echo(f"URL: {example['url']}")
            click.echo("Exemple de date:")

            sample_data = example.get("sample_data", [])
            for i, item in enumerate(sample_data[:2], 1):  # Show first 2
                click.echo(f"  {i}. {item.get('operation')} -> {item.get('result')}")

        click.echo(
            "\nPentru mai multe detalii, folosește: python cli_rest.py history --help"
        )

    except requests.exceptions.RequestException as e:
        click.echo(f"Eroare: {e}", err=True)


@cli.command()
def stats():
    """Afișează statistici despre cache și baza de date"""
    try:
        # Cache stats
        cache_response = requests.get(f"{API_BASE}/cache/stats")
        cache_response.raise_for_status()
        cache_stats = cache_response.json()

        # Database stats
        db_response = requests.get(f"{API_BASE}/database/stats")
        db_response.raise_for_status()
        db_stats = db_response.json()

        click.echo("=== STATISTICI CACHE ===")
        click.echo(json.dumps(cache_stats, indent=2))

        click.echo("\n=== STATISTICI BAZA DE DATE ===")
        click.echo(json.dumps(db_stats, indent=2))

    except requests.exceptions.RequestException as e:
        click.echo(f"Eroare la accesarea statisticilor: {e}", err=True)


@cli.command()
@click.confirmation_option(prompt="Sigur vrei să ștergi cache-ul?")
def clear_cache():
    """Șterge cache-ul"""
    try:
        response = requests.post(f"{API_BASE}/cache/clear")
        response.raise_for_status()
        result = response.json()
        click.echo(result.get("message", "Cache-ul a fost șters."))
    except requests.exceptions.RequestException as e:
        click.echo(f"Eroare la ștergerea cache-ului: {e}", err=True)


if __name__ == "__main__":
    cli()
