import json
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from services.simulation.customer_selector import CustomerSelection


class AtomicDailySelector:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS daily_runs (
                    run_date TEXT PRIMARY KEY,
                    total_customers INTEGER NOT NULL,
                    returning_ratio REAL NOT NULL,
                    selection_json TEXT NOT NULL,
                    seed INTEGER
                )
            """)

        with self.connect() as connection:
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(daily_runs)"
                )
            }
            if "seed" not in columns:
                connection.execute(
                    "ALTER TABLE daily_runs ADD COLUMN seed INTEGER"
                )

    def connect(self):
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def select_for_day(
        self,
        activity_at,
        total_customers,
        returning_ratio=0.30,
        seed=42,
    ):
        if isinstance(total_customers, bool) or not isinstance(
            total_customers, int
        ) or not 1 <= total_customers <= 6000:
            raise ValueError("total_customers must be between 1 and 6000")

        if not isinstance(returning_ratio, (int, float)) or not (
            0 <= returning_ratio <= 1
        ):
            raise ValueError("returning_ratio must be between 0 and 1")

        if not isinstance(activity_at, datetime) or (
            activity_at.tzinfo is None
            or activity_at.utcoffset() is None
        ):
            raise ValueError("activity_at must be timezone-aware")

        activity_at = activity_at.astimezone(timezone.utc)
        run_date = activity_at.date().isoformat()
        timestamp = activity_at.isoformat()

        with self.connect() as connection:
            # Reserve the write transaction before checking for a run.
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                "SELECT * FROM daily_runs WHERE run_date = ?",
                (run_date,),
            ).fetchone()

            if existing is not None:
                if (
                    existing["total_customers"] != total_customers
                    or abs(
                        existing["returning_ratio"] - returning_ratio
                    ) > 1e-9
                ):
                    raise ValueError(
                        "Existing daily run has different configuration"
                    )

                if existing["seed"] is None:
                    raise ValueError(
                        "Existing daily run has no recorded seed; "
                        "cannot safely retry"
                    )
                if existing["seed"] != seed:
                    raise ValueError(
                        "Existing daily run has different seed"
                    )

                data = json.loads(existing["selection_json"])

                return CustomerSelection(
                    customer_ids=data["customer_ids"],
                    new_customer_ids=data["new_customer_ids"],
                    returning_customer_ids=data["returning_customer_ids"],
                )

            rows = connection.execute(
                """
                SELECT customer_id FROM customers
                WHERE first_seen < ?
                ORDER BY customer_id
                """,
                (timestamp,),
            ).fetchall()

            eligible_ids = [row["customer_id"] for row in rows]

            rng = random.Random(seed)
            requested = round(total_customers * returning_ratio)
            returning_count = min(requested, len(eligible_ids))

            returning_ids = rng.sample(
                eligible_ids, returning_count
            )

            new_count = total_customers - returning_count
            new_ids = [
                f"customer-{uuid4().hex}"
                for _ in range(new_count)
            ]

            customer_ids = returning_ids + new_ids
            rng.shuffle(customer_ids)

            for customer_id in customer_ids:
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

            payload = json.dumps({
                "customer_ids": customer_ids,
                "new_customer_ids": new_ids,
                "returning_customer_ids": returning_ids,
            })

            connection.execute(
                """
                INSERT INTO daily_runs (
                    run_date,
                    total_customers,
                    returning_ratio,
                    selection_json,
                    seed
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_date,
                    total_customers,
                    returning_ratio,
                    payload,
                    seed,
                ),
            )

        return CustomerSelection(
            customer_ids=customer_ids,
            new_customer_ids=new_ids,
            returning_customer_ids=returning_ids,
        )

    def count_customers(self):
        with self.connect() as connection:
            return connection.execute(
                "SELECT COUNT(*) FROM customers"
            ).fetchone()[0]

    def count_daily_runs(self):
        with self.connect() as connection:
            return connection.execute(
                "SELECT COUNT(*) FROM daily_runs"
            ).fetchone()[0]
