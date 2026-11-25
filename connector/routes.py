"""
connector/routes.py

Defines all API routes for the AMS Monitoring Connector.

Endpoints:
    GET  /api/logs                        - Fetch all logs from the monitoring provider
    GET  /api/logs/errors                 - Fetch only error/critical logs
    GET  /api/logs/service/{name}         - Fetch logs filtered by service name
    POST /api/logs/query                  - Execute a custom provider-specific query
    GET  /api/observability/summary       - Observability summary of the system
    POST /api/process-incidents           - Fetch error logs and create incidents in the incident platform
    POST /api/newrelic-alert              - Receive a New Relic performance alert
"""
import secrets

from fastapi import APIRouter, Header, HTTPException, status

from config import Config
from connector.models import (
    CustomQueryRequest,
    NewRelicAlert,
    ProcessIncidentRequest
)

from connector.services.monitoring_connector_service import (
    MonitoringConnectorService
)
from shared.logger import get_logger

# Logger scoped to this module for request/response tracing
logger = get_logger("connector.routes")

# All routes are grouped under /api with a shared tag for Swagger UI
router = APIRouter(
    prefix="/api",
    tags=["Monitoring Connector"]
)

# Single shared service instance used by all route handlers
connector_service = MonitoringConnectorService()


# =====================================================
# Logs
# =====================================================

# Returns all logs from the configured monitoring provider (last 1 hour)
@router.get("/logs")
def get_all_logs():
    logger.info("[REQUEST] GET /api/logs - Fetching all logs")
    result = connector_service.get_all_logs()
    logger.info(f"[RESPONSE] GET /api/logs - Returned {len(result)} log(s)")
    return result


# Returns only ERROR and CRITICAL severity logs from the monitoring provider
@router.get("/logs/errors")
def get_error_logs():
    logger.info("[REQUEST] GET /api/logs/errors - Fetching error logs")
    result = connector_service.get_error_logs()
    logger.info(f"[RESPONSE] GET /api/logs/errors - Returned {len(result)} error log(s)")
    return result


# Returns logs filtered by a specific service name passed as a path parameter
@router.get("/logs/service/{service_name}")
def get_logs_by_service(
    service_name: str
):
    logger.info(f"[REQUEST] GET /api/logs/service/{service_name} - Fetching logs for service")
    result = connector_service.get_logs_by_service(service_name)
    logger.info(f"[RESPONSE] GET /api/logs/service/{service_name} - Returned {len(result)} log(s)")
    return result


# Accepts a raw NRQL/provider query string and executes it directly against the monitoring provider
@router.post("/logs/query")
def execute_custom_query(
    request: CustomQueryRequest
):
    logger.info(f"[REQUEST] POST /api/logs/query - Query : {request.query}")
    result = connector_service.execute_custom_query(request.query)
    logger.info(f"[RESPONSE] POST /api/logs/query - Returned {len(result)} result(s)")
    return result


# =====================================================
# Observability
# =====================================================

# Returns a health summary of the system — total logs, error count, critical count, top error services
@router.get("/observability/summary")
def get_observability_summary():
    logger.info("[REQUEST] GET /api/observability/summary - Building observability summary")
    result = connector_service.get_observability_summary()
    logger.info(f"[RESPONSE] GET /api/observability/summary - Total: {result['totalLogs']} | Errors: {result['errorLogs']} | Critical: {result['criticalLogs']}")
    return result


# =====================================================
# Incident Processing
# =====================================================

# Triggers the full pipeline: fetch error logs → map to incidents → create incidents in the incident platform
@router.post("/process-incidents")
def process_incidents(
    request: ProcessIncidentRequest
):
    logger.info("[REQUEST] POST /api/process-incidents - Starting incident processing")
    result = connector_service.process_incidents(request)
    logger.info(f"[RESPONSE] POST /api/process-incidents - Processed: {result['processedLogs']} | Created: {result['incidentsCreated']} | Failed: {result['failed']}")
    return result


# =====================================================
# New Relic performance alerts
# =====================================================

@router.post("/newrelic-alert", status_code=status.HTTP_202_ACCEPTED)
def receive_newrelic_alert(
    alert: NewRelicAlert,
    x_connector_token: str | None = Header(default=None),
):
    """Accept a New Relic performance alert during the simulation integration phase."""
    expected_token = Config.NEW_RELIC_WEBHOOK_TOKEN
    if not expected_token:
        logger.error("[NEW_RELIC_ALERT] Rejected because NEW_RELIC_WEBHOOK_TOKEN is not configured")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="New Relic webhook is not configured.")
    if not x_connector_token or not secrets.compare_digest(x_connector_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid connector token.")

    if Config.PERFORMANCE_SIMULATION_ONLY and alert.environment.lower() != Config.PERFORMANCE_SIMULATION_ENVIRONMENT.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only '{Config.PERFORMANCE_SIMULATION_ENVIRONMENT}' alerts are accepted while simulation mode is enabled.",
        )

    logger.info(
        "[NEW_RELIC_ALERT] Accepted | "
        f"id={alert.alert_id} state={alert.alert_state} service={alert.service} "
        f"environment={alert.environment} severity={alert.severity} "
        f"cpu={alert.cpu_percent} latency={alert.p95_latency_seconds} error_rate={alert.error_rate_percent}"
    )
    return connector_service.process_newrelic_alert(alert)