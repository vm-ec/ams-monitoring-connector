"""
connector/scheduler.py

Background scheduler that automatically polls for new error logs
and triggers incident processing at a configured interval.

Fetches error logs from New Relic and filters by each log's own timestamp
to detect only new errors since the last run.
"""
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from connector.models import ProcessIncidentRequest
from connector.store import save_run
from shared.logger import get_logger

logger = get_logger("connector.scheduler")

# Tracks the last time the scheduler ran — only logs with timestamp after this are processed
_last_checked: datetime = datetime.now(timezone.utc)


def _run_pipeline():
    """Fetch error logs, filter by each log's timestamp, trigger process_incidents if new errors found."""
    global _last_checked

    from monitoring.services.monitoring_service import MonitoringService
    from connector.services.monitoring_connector_service import MonitoringConnectorService

    now = datetime.now(timezone.utc)
    logger.info(f"[SCHEDULER] Checking for new errors since {_last_checked.isoformat()}")

    try:
        # Step 1 — Fetch all error logs from New Relic
        monitoring_service = MonitoringService()
        error_logs = monitoring_service.get_error_logs()
        logger.info(f"[SCHEDULER] Fetched {len(error_logs)} error log(s) from monitoring provider")

        # Step 2 — Filter logs where the log's own timestamp is after _last_checked
        new_errors = []
        for log in error_logs:
            raw_ts = log.get("timestamp") if isinstance(log, dict) else getattr(log, "timestamp", None)
            if raw_ts is None:
                continue
            # New Relic returns timestamp in milliseconds
            log_time = datetime.fromtimestamp(int(raw_ts) / 1000, tz=timezone.utc)
            if log_time > _last_checked:
                new_errors.append(log)

        logger.info(f"[SCHEDULER] {len(new_errors)} new error(s) found after {_last_checked.isoformat()}")

        # Step 3 — Trigger process_incidents only if new errors exist
        if new_errors:
            connector_service = MonitoringConnectorService()
            result = connector_service.process_incidents(ProcessIncidentRequest())
            logger.info(
                f"[SCHEDULER] Done | Processed: {result['processedLogs']} | "
                f"Created: {result['incidentsCreated']} | Skipped: {result['skipped']} | Failed: {result['failed']}"
            )
            save_run({
                "ran_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "new_errors_found": len(new_errors),
                "processedLogs": result["processedLogs"],
                "incidentsCreated": result["incidentsCreated"],
                "skipped": result["skipped"],
                "failed": result["failed"],
                "decisions": result["decisions"]
            })
        else:
            logger.info("[SCHEDULER] No new errors — skipping incident processing")
            save_run({
                "ran_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "new_errors_found": 0,
                "processedLogs": 0,
                "incidentsCreated": 0,
                "skipped": 0,
                "failed": 0,
                "decisions": []
            })

    except Exception as ex:
        logger.error(f"[SCHEDULER] Pipeline failed: {ex}")

    _last_checked = now


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_pipeline,
        trigger="interval",
        minutes=Config.SCHEDULER_INTERVAL_MINUTES,
        id="incident_pipeline",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc)
    )
    scheduler.start()
    logger.info(f"[SCHEDULER] Started — polling every {Config.SCHEDULER_INTERVAL_MINUTES} minute(s)")
    return scheduler
