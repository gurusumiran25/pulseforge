from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from services.simulation.atomic_daily_selector import AtomicDailySelector
from services.simulation.session_planner import plan_daily_sessions
from services.simulation.persona_journey import generate_persona_journey
from services.storage.sqlite_store import SQLiteEventStore


@dataclass(frozen=True)
class DailySimulationSummary:
    run_date: str
    customers: int
    new_customers: int
    returning_customers: int
    sessions: int
    generated_events: int
    successful_purchases: int
    events_before: int
    events_after: int
    newly_stored_events: int


class DailySimulationOrchestrator:
    def __init__(self, simulation_db_path, event_db_path):
        self.simulation_db_path = Path(simulation_db_path)
        self.event_db_path = Path(event_db_path)

        if self.simulation_db_path.resolve() == self.event_db_path.resolve():
            raise ValueError(
                "Simulation and event databases must use separate paths"
            )

        self.selector = AtomicDailySelector(self.simulation_db_path)
        self.event_store = SQLiteEventStore(self.event_db_path)

    def run(
        self,
        activity_at: datetime,
        total_customers: int,
        returning_ratio: float = 0.30,
        seed: int = 42,
    ) -> DailySimulationSummary:

        if not isinstance(activity_at, datetime) or (
            activity_at.tzinfo is None
            or activity_at.utcoffset() is None
        ):
            raise ValueError("activity_at must be timezone-aware")

        activity_at = activity_at.astimezone(timezone.utc)

        selection = self.selector.select_for_day(
            activity_at=activity_at,
            total_customers=total_customers,
            returning_ratio=returning_ratio,
            seed=seed,
        )

        sessions = plan_daily_sessions(
            selection.customer_ids,
            activity_at,
            seed=seed,
        )

        events = []
        for session in sessions:
            events.extend(generate_persona_journey(session))

        before = self.event_store.count_events()

        self.event_store.insert_events_bulk(events)

        after = self.event_store.count_events()

        purchases = sum(
            event.event_name == "payment_succeeded"
            for event in events
        )

        return DailySimulationSummary(
            run_date=activity_at.date().isoformat(),
            customers=len(selection.customer_ids),
            new_customers=len(selection.new_customer_ids),
            returning_customers=len(selection.returning_customer_ids),
            sessions=len(sessions),
            generated_events=len(events),
            successful_purchases=purchases,
            events_before=before,
            events_after=after,
            newly_stored_events=after - before,
        )
