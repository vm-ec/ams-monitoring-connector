"""Durable idempotency store for New Relic performance alerts."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class AlertStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS newrelic_alerts (
                    alert_id TEXT PRIMARY KEY,
                    alert_state TEXT NOT NULL,
                    status TEXT NOT NULL,
                    service TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    incident_number TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_error TEXT
                )
                """
            )

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def claim_open_alert(self, alert_id: str, alert_state: str, service: str, environment: str) -> bool:
        """Claim a new alert for incident creation. Returns False if it was seen before."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT status FROM newrelic_alerts WHERE alert_id = ?", (alert_id,)
            ).fetchone()
            if existing:
                if existing[0] != "FAILED":
                    return False
                connection.execute(
                    """
                    UPDATE newrelic_alerts
                    SET alert_state = ?, status = 'PROCESSING', service = ?, environment = ?,
                        updated_at = ?, last_error = NULL
                    WHERE alert_id = ?
                    """,
                    (alert_state, service, environment, now, alert_id),
                )
                return True

            connection.execute(
                """
                INSERT INTO newrelic_alerts
                    (alert_id, alert_state, status, service, environment, created_at, updated_at)
                VALUES (?, ?, 'PROCESSING', ?, ?, ?, ?)
                """,
                (alert_id, alert_state, service, environment, now, now),
            )
            return True

    def get(self, alert_id: str) -> dict | None:
        with self._connection() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM newrelic_alerts WHERE alert_id = ?", (alert_id,)
            ).fetchone()
            return dict(row) if row else None

    def mark_created(self, alert_id: str, incident_number: str) -> None:
        self._update(alert_id, "CREATED", incident_number=incident_number)

    def mark_failed(self, alert_id: str, error: str) -> None:
        self._update(alert_id, "FAILED", error=error)

    def _update(self, alert_id: str, status: str, incident_number: str | None = None, error: str | None = None) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE newrelic_alerts
                SET status = ?, incident_number = COALESCE(?, incident_number),
                    last_error = ?, updated_at = ?
                WHERE alert_id = ?
                """,
                (status, incident_number, error, datetime.now(timezone.utc).isoformat(), alert_id),
            )