import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_FILE = Path(__file__).parent.parent / "operations.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,
            input TEXT NOT NULL,
            result TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """
    )

    # Adaugă un index pentru performanță
    cursor.execute(
        """
                   CREATE INDEX IF NOT EXISTS idx_operation_input
                       ON operations (operation, input)
                   """
    )

    conn.commit()
    conn.close()


def save_operation(operation: str, input_data: str, result: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO operations (operation, input, result, timestamp)
        VALUES (?, ?, ?, ?)
    """,
        (operation, input_data, result, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    logger.info(f"Salvat în DB: {operation}({input_data}) = {result}")


def get_all_operations(
    operation_filter: Optional[str] = None, input_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns ALL operations including duplicates with optional filtering

    Args:
        operation_filter: Filter by operation type (e.g., 'pow', 'fibonacci', 'factorial')
        input_filter: Filter by input value or pattern

    Returns:
        List of dictionaries containing all operations
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Base query
    query = "SELECT operation, input, result, timestamp FROM operations"
    params = []
    conditions = []

    # Add filters if provided
    if operation_filter:
        conditions.append("operation = ?")
        params.append(operation_filter)

    if input_filter:
        conditions.append("input LIKE ?")
        params.append(f"%{input_filter}%")

    # Build final query
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Format results
    result = []
    for op, inp, res, ts in rows:
        try:
            input_parsed = json.loads(inp) if inp else None
        except json.JSONDecodeError:
            input_parsed = inp

        try:
            result_parsed = json.loads(res) if res else None
        except json.JSONDecodeError:
            result_parsed = res

        result.append(
            {
                "operation": op,
                "input": input_parsed,
                "result": result_parsed,
                "timestamp": ts,
            }
        )

    logger.info(
        f"Retrieved {len(result)} total operations with filters: operation={operation_filter}, input={input_filter}"
    )
    return result


def get_unique_operations(
    operation_filter: Optional[str] = None, input_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns unique operations based on operation and input combination
    Only the most recent entry for each unique combination is returned

    Args:
        operation_filter: Filter by operation type (e.g., 'pow', 'fibonacci', 'factorial')
        input_filter: Filter by input value or pattern

    Returns:
        List of dictionaries containing unique operation combinations
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Query to get the most recent entry for each unique combination
    query = """
            SELECT o1.operation, o1.input, o1.result, o1.timestamp
            FROM operations o1
                     INNER JOIN (SELECT operation, input, MAX (timestamp) as max_timestamp \
                                 FROM operations \
            """

    params = []
    conditions = []

    # Add filters to the subquery
    if operation_filter:
        conditions.append("operation = ?")
        params.append(operation_filter)

    if input_filter:
        conditions.append("input LIKE ?")
        params.append(f"%{input_filter}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += """
            GROUP BY operation, input
        ) o2 ON o1.operation = o2.operation
           AND o1.input = o2.input
           AND o1.timestamp = o2.max_timestamp
        ORDER BY o1.timestamp DESC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Format results
    result = []
    for op, inp, res, ts in rows:
        try:
            input_parsed = json.loads(inp) if inp else None
        except json.JSONDecodeError:
            input_parsed = inp

        try:
            result_parsed = json.loads(res) if res else None
        except json.JSONDecodeError:
            result_parsed = res

        result.append(
            {
                "operation": op,
                "input": input_parsed,
                "result": result_parsed,
                "timestamp": ts,
            }
        )

    logger.info(
        f"Retrieved {len(result)} unique operations with filters: operation={operation_filter}, input={input_filter}"
    )
    return result


def get_db_stats():
    """Returns database statistics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Total operations
    cursor.execute("SELECT COUNT(*) FROM operations")
    total = cursor.fetchone()[0]

    # Unique combinations
    cursor.execute("SELECT COUNT(DISTINCT operation || input) FROM operations")
    unique = cursor.fetchone()[0]

    # Operations by type
    cursor.execute("SELECT operation, COUNT(*) FROM operations GROUP BY operation")
    by_operation = dict(cursor.fetchall())

    conn.close()

    return {
        "total_operations": total,
        "unique_combinations": unique,
        "duplicates": total - unique,
        "by_operation": by_operation,
    }


# Test functions
def test_db_functions():
    """Test function to verify database operations work correctly"""
    try:
        # Initialize database
        init_db()

        # Test save operation
        test_input = json.dumps({"x": 2, "y": 3})
        test_result = json.dumps({"x": 2, "y": 3, "result": 8})
        save_operation("pow", test_input, test_result)

        # Test get all operations
        all_ops = get_all_operations()
        print(f"Total operations: {len(all_ops)}")

        # Test get unique operations
        unique_ops = get_unique_operations()
        print(f"Unique operations: {len(unique_ops)}")

        # Test with filters
        pow_ops = get_unique_operations(operation_filter="pow")
        print(f"Pow operations: {len(pow_ops)}")

        # Test stats
        stats = get_db_stats()
        print(f"Database stats: {stats}")

        return True

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    # Run tests
    success = test_db_functions()
    if success:
        print("✅ All database functions working correctly")
    else:
        print("❌ Database tests failed")
