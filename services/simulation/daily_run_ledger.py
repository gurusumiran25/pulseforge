import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from services.simulation.customer_selector import (
    CustomerSelection,
    CustomerSelector,
)


class DailyRunLedger:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS daily_runs (
                    run_date TEXT PRIMARY KEY,
                    total_customers INTEGER NOT NULL,
                    returning_ratio REAL NOT NULL,
                    selection_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'selected'
                )
            """)

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def select_for_day(
        self,
        selector: CustomerSelector,
        activity_at: datetime,
        total_customers: int,
        returning_ratio: float = 0.30,
    ):
        if (
            activity_at.tzinfo is None
            or activity_at.utcoffset() is None
        ):
            raise ValueError("activity_at must be timezone-aware")

        activity_at = activity_at.astimezone(timezone.utc)
        run_date = activity_at.date().isoformat()

        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM daily_runs WHERE run_date = ?",
                (run_date,),
            ).fetchone()

        if row is not None:
            if (
                row["total_customers"] != total_customers
                or abs(row["returning_ratio"] - returning_ratio) > 1e-9
            ):
                raise ValueError(
                    "Existing daily run has different configuration"
                )

            data = json.loads(row["selection_json"])

            return CustomerSelection(
                customer_ids=data["customer_ids"],
                new_customer_ids=data["new_customer_ids"],
                returning_customer_ids=data["returning_customer_ids"],
            )

        selection = selector.select_daily_customers(
            total_customers=total_customers,
            returning_ratio=returning_ratio,
            activity_at=activity_at,
        )

        payload = json.dumps({
            "customer_ids": selection.customer_ids,
            "new_customer_ids": selection.new_customer_ids,
            "returning_customer_ids": selection.returning_customer_ids,
        })

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO daily_runs (
                    run_date,
                    total_customers,
                    returning_ratio,
                    selection_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    run_date,
                    total_customers,
                    returning_ratio,
                    payload,
                ),
            )

        return selection
