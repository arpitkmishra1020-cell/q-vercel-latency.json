from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cors_header(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: float


def percentile(values, p):
    values = sorted(values)

    if not values:
        return 0

    position = (len(values) - 1) * (p / 100)
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return values[lower]

    return (
        values[lower]
        + (values[upper] - values[lower]) * (position - lower)
    )


def load_data():
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "q-vercel-latency.json"
    )

    with open(path, "r") as f:
        return json.load(f)


@app.post("/api/latency")
def calculate_latency(request: LatencyRequest):

    data = load_data()

    results = []

    for region in request.regions:

        region_data = [
            row for row in data
            if row["region"] == region
        ]

        if not region_data:
            continue

        latencies = [
            row["latency_ms"]
            for row in region_data
        ]

        uptimes = [
            row["uptime_pct"]
            for row in region_data
        ]

        results.append({
            "region": region,
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile(latencies, 95),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                1 for latency in latencies
                if latency > request.threshold_ms
            )
        })

    return results
