import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class CustomerRegistry:
    def __init__(self, db_path="data/storage/customers.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
                """
            )

    def register_customer(self, customer_id, seen_at=None):
        if not customer_id or not customer_id.strip():
            raise ValueError("customer_id must not be empty")

        if seen_at is None:
            seen_at = datetime.now(timezone.utc)

        if seen_at.tzinfo is None or seen_at.utcoffset() is None:
            raise ValueError("seen_at must be timezone-aware")

        timestamp = seen_at.astimezone(timezone.utc).isoformat()

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO customers (
                    customer_id, first_seen, last_seen
                )
                VALUES (?, ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET
                    first_seen = MIN(
                        customers.first_seen,
                        excluded.first_seen
                    ),
                    last_seen = MAX(
                        customers.last_seen,
                        excluded.last_seen
                    )
                """,
                (customer_id, timestamp, timestamp),
            )

    def get_customer(self, customer_id):
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT customer_id, first_seen, last_seen
                FROM customers
                WHERE customer_id = ?
                """,
                (customer_id,),
            ).fetchone()

        return dict(row) if row else None

    def count_customers(self):
        with self.connect() as connection:
            return connection.execute(
                "SELECT COUNT(*) FROM customers"
            ).fetchone()[0]
