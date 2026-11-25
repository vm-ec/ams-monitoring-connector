"""
connector/app.py

Entry point for the AMS Monitoring Connector FastAPI application.
Initializes the app, registers routes, and logs startup configuration.
"""
import uvicorn

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from config import Config
from connector.routes import router
from connector.scheduler import start_scheduler
from connector.store import pipeline_runs
from shared.logger import get_logger

# Create a logger scoped to this module
logger = get_logger("connector.app")

# Initialize the FastAPI application with metadata from config
app = FastAPI(
    title=Config.APPLICATION_NAME,
    version=Config.APPLICATION_VERSION,
    description="Generic Monitoring Connector"
)

# Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Register all /api routes defined in connector/routes.py
app.include_router(router)

# Start the background scheduler — auto-polls for errors and creates incidents
# Polling is optional: direct New Relic webhook tests must not process historic logs.
if Config.SCHEDULER_ENABLED:
    start_scheduler()
    logger.info("[SCHEDULER] Enabled")
else:
    logger.info("[SCHEDULER] Disabled by SCHEDULER_ENABLED=false")

# Log startup configuration so it is visible in Render logs on boot
logger.info("[STEP 1] AMS Monitoring Connector starting up")
logger.info(f"[STEP 2] Environment        : {Config.ENVIRONMENT}")
logger.info(f"[STEP 3] Monitoring Provider : {Config.MONITORING_PROVIDER}")
logger.info(f"[STEP 4] Incident Provider   : {Config.INCIDENT_PROVIDER}")
logger.info(f"[STEP 5] Listening on        : {Config.CONNECTOR_HOST}:{Config.CONNECTOR_PORT}")


# Health check endpoint — returns app metadata and current status
@app.get("/")
def home():
    return {
        "application": Config.APPLICATION_NAME,
        "version": Config.APPLICATION_VERSION,
        "environment": Config.ENVIRONMENT,
        "monitoringProvider": Config.MONITORING_PROVIDER,
        "incidentProvider": Config.INCIDENT_PROVIDER,
        "status": "Running"
    }


# Dashboard — visual UI showing scheduler runs, decisions, and incidents
@app.get("/dashboard")
def dashboard(request: Request):
    total_created = sum(r["incidentsCreated"] for r in pipeline_runs)
    total_skipped = sum(r["skipped"] for r in pipeline_runs)
    total_errors  = sum(r["new_errors_found"] for r in pipeline_runs)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "runs": pipeline_runs,
            "total_runs": len(pipeline_runs),
            "total_errors": total_errors,
            "total_created": total_created,
            "total_skipped": total_skipped,
            "monitoring_provider": Config.MONITORING_PROVIDER,
            "incident_provider": Config.INCIDENT_PROVIDER
        }
    )


# Entry point when running the file directly (python connector/app.py)
if __name__ == "__main__":

    uvicorn.run(
        "connector.app:app",
        host=Config.CONNECTOR_HOST,
        port=Config.CONNECTOR_PORT,
        reload=True
    )
