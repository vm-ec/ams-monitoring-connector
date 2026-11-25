"""
connector/models.py

Request models for the Connector API endpoints.

Models:
    CustomQueryRequest      - Payload for POST /api/logs/query
    ProcessIncidentRequest  - Payload for POST /api/process-incidents
    NewRelicAlert           - Payload for POST /api/newrelic-alert
"""
from pydantic import BaseModel, Field


# Request body for POST /api/logs/query
# Accepts a raw query string to be executed directly against the monitoring provider
class CustomQueryRequest(BaseModel):

    query: str  # Provider-specific query e.g. NRQL for New Relic


# Request body for POST /api/process-incidents
# Both fields are optional filters — if omitted, all error logs are processed
class ProcessIncidentRequest(BaseModel):

    service_name: str | None = None  # Filter incidents to a specific service

    severity: str | None = None      # Filter incidents to a specific severity level


class NewRelicAlert(BaseModel):
    """Normalized performance alert received from a New Relic workflow."""

    alert_id: str = Field(min_length=1)
    alert_state: str = "OPEN"
    service: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    severity: str = "CRITICAL"
    application: str | None = None
    host_name: str | None = None
    ec2_instance_id: str | None = None
    cpu_percent: float | None = None
    memory_percent: float | None = None
    p95_latency_seconds: float | None = None
    error_rate_percent: float | None = None
    alert_url: str | None = None
    started_at: str | None = None
    labels: list[str] = Field(default_factory=list)