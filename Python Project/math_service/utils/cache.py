import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# cache-ul e un dictionar global (atenție: NU thread-safe)
memory_cache: Dict[Tuple[str, str], str] = {}


def get_from_cache(operation: str, input_data: str) -> str | None:
    cache_key = (operation, input_data)
    cached_result = memory_cache.get(cache_key)

    if cached_result:
        logger.info(
            f"CACHE HIT pentru {operation}({input_data}) - nu se va salva în DB"
        )
    else:
        logger.info(
            f"CACHE MISS pentru {operation}({input_data}) - se va calcula și salva"
        )

    return cached_result


def set_in_cache(operation: str, input_data: str, result: str):
    global memory_cache
    print(f"In set_in_cache - memory_cache id: {id(memory_cache)}")
    print(f"In set_in_cache - memory_cache before: {memory_cache}")

    cache_key = (operation, input_data)
    memory_cache[cache_key] = result

    print(f"In set_in_cache - memory_cache after: {memory_cache}")
    logger.info(f"Salvat în cache: {operation}({input_data}) = {result}")


def get_cache_stats():
    """Returnează statistici despre cache"""
    return {
        "total_cached_operations": len(memory_cache),
        "cached_keys": [f"{op}({inp})" for op, inp in memory_cache.keys()],
        "cache_size_mb": len(str(memory_cache)) / (1024 * 1024),
    }


def clear_cache():
    """Curăță cache-ul complet"""
    global memory_cache
    old_size = len(memory_cache)
    memory_cache = {}
    logger.info(f"Cache-ul a fost curățat complet ({old_size} intrări eliminate)")


def get_cache():
    """Return the current cache dictionary"""
    return memory_cache
