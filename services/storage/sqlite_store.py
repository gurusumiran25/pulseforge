import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from contracts.event_validation import EventEnvelope


DEFAULT_DB_PATH = Path("data/storage/pulseforge.db")


class SQLiteEventStore:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_name TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_session
                ON events(session_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_name
                ON events(event_name)
                """
            )

    def insert_event(self, event: EventEnvelope):
        ingested_at = datetime.now(timezone.utc).isoformat()
        stored_event = event.model_copy(
            update={"ingested_at": datetime.fromisoformat(ingested_at)}
        )

        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_id,
                    event_name,
                    user_id,
                    session_id,
                    event_time,
                    ingested_at,
                    payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored_event.event_id,
                    stored_event.event_name,
                    stored_event.user_id,
                    stored_event.session_id,
                    stored_event.event_time.isoformat(),
                    ingested_at,
                    stored_event.model_dump_json(),
                ),
            )

            return cursor.rowcount == 1

    def count_events(self):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM events"
            ).fetchone()
            return row["total"]

    def get_event(self, event_id):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM events WHERE event_id = ?",
                (event_id,),
            ).fetchone()

        if row is None:
            return None

        return EventEnvelope.model_validate_json(row["payload"])

    def insert_events_bulk(self, events):
        """Insert multiple validated events in one SQLite transaction."""
        if not events:
            return {"inserted": 0, "duplicates": 0}

        inserted = 0
        ingested_at = datetime.now(timezone.utc)

        with self.connect() as connection:
            for event in events:
                stored_event = event.model_copy(
                    update={"ingested_at": ingested_at}
                )

                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO events (
                        event_id, event_name, user_id, session_id,
                        event_time, ingested_at, payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        stored_event.event_id,
                        stored_event.event_name,
                        stored_event.user_id,
                        stored_event.session_id,
                        stored_event.event_time.isoformat(),
                        ingested_at.isoformat(),
                        stored_event.model_dump_json(),
                    ),
                )

                inserted += cursor.rowcount

        return {
            "inserted": inserted,
            "duplicates": len(events) - inserted,
        }
