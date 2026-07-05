"""
Metrics Analytics API
----------------------
Jednostavan backend REST servis za prikupljanje i analizu metrika.
Namenjen za demonstraciju deployment-a na Google Cloud Run
(kontejnerizacija, environment promenljive, Secret Manager, monitoring, CI/CD).
"""

import os
import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Konfiguracija preko environment promenljivih
# (namerno se NE hardkoduju u kodu - podešavaju se kroz Cloud Run)
# ---------------------------------------------------------------------------
APP_ENV = os.getenv("APP_ENV", "development")
ERROR_RATE = float(os.getenv("ERROR_RATE", "0.5"))  # procenat (0.0 - 1.0) za /simulate/error

# API_KEY se NE hardkoduje - Cloud Run je popunjava iz Secret Manager-a
# preko --set-secrets pri deployment-u. Ako ne postoji (npr. lokalno pokretanje
# bez podešenog secreta), koristi se placeholder da aplikacija i dalje radi.
API_KEY = os.getenv("API_KEY", "not-configured")

app = FastAPI(
    title="Metrics Analytics API",
    description="Servis za prikupljanje, pregled i analizu metrika. "
                "Razvijen kao projekat iz predmeta Cloud infrastrukture i servisi.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# In-memory "baza" podataka
# (namerno pojednostavljeno - fokus projekta je cloud deployment, ne baza)
# ---------------------------------------------------------------------------
metrics_db: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Pydantic modeli
# ---------------------------------------------------------------------------
class MetricCreate(BaseModel):
    name: str = Field(..., examples=["page_views"])
    value: float = Field(..., examples=[42.0])
    tags: Optional[dict] = Field(default=None, examples=[{"region": "EU", "source": "mobile"}])


class MetricRecord(MetricCreate):
    id: str
    timestamp: str


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "environment": APP_ENV,
        "time": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# CRUD - Create
# ---------------------------------------------------------------------------
@app.post("/metrics", response_model=MetricRecord, status_code=201, tags=["Metrics"])
def create_metric(metric: MetricCreate):
    metric_id = str(uuid.uuid4())
    record = {
        "id": metric_id,
        "name": metric.name,
        "value": metric.value,
        "tags": metric.tags,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    metrics_db[metric_id] = record
    return record


# ---------------------------------------------------------------------------
# CRUD - Read (lista, sa opcionim filterom po imenu)
# ---------------------------------------------------------------------------
@app.get("/metrics", response_model=list[MetricRecord], tags=["Metrics"])
def list_metrics(name: Optional[str] = None):
    results = list(metrics_db.values())
    if name:
        results = [m for m in results if m["name"] == name]
    return results


# ---------------------------------------------------------------------------
# CRUD - Read (jedan zapis)
# ---------------------------------------------------------------------------
@app.get("/metrics/{metric_id}", response_model=MetricRecord, tags=["Metrics"])
def get_metric(metric_id: str):
    record = metrics_db.get(metric_id)
    if not record:
        raise HTTPException(status_code=404, detail="Metric not found")
    return record


# ---------------------------------------------------------------------------
# CRUD - Delete
# ---------------------------------------------------------------------------
@app.delete("/metrics/{metric_id}", status_code=204, tags=["Metrics"])
def delete_metric(metric_id: str):
    if metric_id not in metrics_db:
        raise HTTPException(status_code=404, detail="Metric not found")
    del metrics_db[metric_id]
    return None


# ---------------------------------------------------------------------------
# Analitički endpoint - agregacija po imenu metrike
# ---------------------------------------------------------------------------
@app.get("/analytics/summary", tags=["Analytics"])
def analytics_summary():
    summary = {}
    for record in metrics_db.values():
        name = record["name"]
        summary.setdefault(name, []).append(record["value"])

    result = {}
    for name, values in summary.items():
        result[name] = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": round(sum(values) / len(values), 2),
        }
    return result


# ---------------------------------------------------------------------------
# Simulacija kašnjenja (za testiranje monitoringa / cold start ponašanja)
# ---------------------------------------------------------------------------
@app.get("/simulate/slow", tags=["Simulation"])
def simulate_slow():
    import time

    delay = random.uniform(1, 5)
    time.sleep(delay)
    return {"message": "Completed after delay", "delay_seconds": round(delay, 2)}


# ---------------------------------------------------------------------------
# Simulacija greške (za testiranje logova i alertinga)
# ERROR_RATE se podešava preko environment promenljive
# ---------------------------------------------------------------------------
@app.get("/simulate/error", tags=["Simulation"])
def simulate_error():
    if random.random() < ERROR_RATE:
        raise HTTPException(status_code=500, detail="Simulated internal server error")
    return {"message": "No error this time", "error_rate": ERROR_RATE}


# ---------------------------------------------------------------------------
# Demonstracija da je secret uspešno učitan (bez otkrivanja pune vrednosti -
# u produkciji se nikad ne vraća ceo secret kroz API odgovor)
# ---------------------------------------------------------------------------
@app.get("/config/secret-status", tags=["System"])
def secret_status():
    is_configured = API_KEY != "not-configured"
    masked = f"{API_KEY[:3]}{'*' * (len(API_KEY) - 3)}" if is_configured else None
    return {
        "secret_configured": is_configured,
        "masked_value": masked,
    }


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/", tags=["System"])
def root():
    return {
        "service": "Metrics Analytics API",
        "environment": APP_ENV,
        "docs": "/docs",
    }
