from collections import deque
from threading import Lock, Thread
from time import sleep, time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from bafend import Astronaut

astronaut = Astronaut("Alex Morgan", 34, 65, 98, 36.7, (115, 75), 14)
UPDATE_INTERVAL = 1.0
HISTORY_LIMIT = 600
ALERT_CONFIRM_SAMPLES = 5
ALERT_CLEAR_SAMPLES = 8
app = FastAPI(title="AstroTrack", version="0.3.0")
lock = Lock()
history: deque[dict[str, Any]] = deque(maxlen=HISTORY_LIMIT)
latest_assessment: dict[str, Any] | None = None
assessment_condition: str | None = None
alert_state: dict[str, dict[str, Any]] = {}


class Assessment(BaseModel):
    alert_id: str
    feeling: str
    symptoms: list[str] = Field(default_factory=list)
    notes: str = ""


def snapshot() -> dict[str, Any]:
    reading = astronaut.generate_reading()
    reading["timestamp"] = time()
    return reading


def evaluate_status(reading: dict[str, Any]) -> dict[str, str]:
    bp = reading["blood_pressure"]
    values = {
        "heart_rate": reading["heart_rate"],
        "blood_oxygen": reading["blood_oxygen"],
        "temperature": reading["temperature"],
        "systolic": bp["systolic"],
        "diastolic": bp["diastolic"],
        "respiratory_rate": reading["respiratory_rate"],
    }
    bands = {
        "heart_rate": (45, 110),
        "blood_oxygen": (93, 100),
        "temperature": (35.8, 38.0),
        "systolic": (85, 130),
        "diastolic": (50, 90),
        "respiratory_rate": (9, 24),
    }
    return {
        key: "normal" if low <= value <= high else "warning"
        for key, value in values.items()
        for low, high in [bands[key]]
    }


def alert_conditions(
    reading: dict[str, Any], samples: list[dict[str, Any]]
) -> dict[str, tuple[bool, bool, str, str]]:
    bp = reading["blood_pressure"]
    checks = {
        "heart_rate-range": (
            reading["heart_rate"] < 45 or reading["heart_rate"] > 110,
            48 <= reading["heart_rate"] <= 105,
            "Heart rate remains outside the alert range",
            "How are you feeling right now?",
        ),
        "blood_oxygen-range": (
            reading["blood_oxygen"] < 93,
            reading["blood_oxygen"] >= 94,
            "Blood oxygen remains below the alert range",
            "Have you noticed any change in your breathing or energy?",
        ),
        "temperature-range": (
            reading["temperature"] < 35.8 or reading["temperature"] > 38.0,
            36.0 <= reading["temperature"] <= 37.8,
            "Temperature remains outside the alert range",
            "Have you been feeling unusually warm or unwell?",
        ),
        "systolic-range": (
            bp["systolic"] < 85 or bp["systolic"] > 130,
            88 <= bp["systolic"] <= 125,
            "Systolic pressure remains outside the alert range",
            "How are you feeling right now?",
        ),
        "diastolic-range": (
            bp["diastolic"] < 50 or bp["diastolic"] > 90,
            53 <= bp["diastolic"] <= 87,
            "Diastolic pressure remains outside the alert range",
            "How are you feeling right now?",
        ),
        "respiratory_rate-range": (
            reading["respiratory_rate"] < 9 or reading["respiratory_rate"] > 24,
            10 <= reading["respiratory_rate"] <= 22,
            "Respiratory rate remains outside the alert range",
            "Have you noticed any change in your breathing?",
        ),
    }
    if len(samples) >= 20:
        previous = samples[-20:-10]
        recent = samples[-10:]
        previous_o2 = sum(item["blood_oxygen"] for item in previous) / 10
        recent_o2 = sum(item["blood_oxygen"] for item in recent) / 10
        previous_hr = sum(item["heart_rate"] for item in previous) / 10
        recent_hr = sum(item["heart_rate"] for item in recent) / 10
        checks["oxygen-trend"] = (
            previous_o2 - recent_o2 >= 3.0,
            previous_o2 - recent_o2 < 1.5,
            "Blood oxygen shows a sustained downward trend",
            "Have you noticed any change in your breathing or energy?",
        )
        checks["heart-rate-trend"] = (
            recent_hr - previous_hr >= 18,
            recent_hr - previous_hr < 9,
            "Heart rate shows a sustained upward trend",
            "Have you recently felt unusually warm, weak, or light-headed?",
        )
    else:
        checks["oxygen-trend"] = (
            False,
            True,
            "Blood oxygen shows a sustained downward trend",
            "Have you noticed any change in your breathing or energy?",
        )
        checks["heart-rate-trend"] = (
            False,
            True,
            "Heart rate shows a sustained upward trend",
            "Have you recently felt unusually warm, weak, or light-headed?",
        )
    return checks


def update_alert_state(reading: dict[str, Any], samples: list[dict[str, Any]]) -> None:
    checks = alert_conditions(reading, samples)
    for alert_id, (trigger, recovered, message, prompt) in checks.items():
        state = alert_state.setdefault(
            alert_id,
            {
                "active": False,
                "bad_count": 0,
                "clear_count": 0,
                "message": message,
                "prompt": prompt,
            },
        )
        if trigger:
            state["bad_count"] += 1
            state["clear_count"] = 0
        elif recovered:
            state["clear_count"] += 1
            state["bad_count"] = 0
        else:
            state["bad_count"] = 0
            state["clear_count"] = 0
        if not state["active"] and state["bad_count"] >= ALERT_CONFIRM_SAMPLES:
            state["active"] = True
        elif state["active"] and state["clear_count"] >= ALERT_CLEAR_SAMPLES:
            state["active"] = False
        state["message"] = message
        state["prompt"] = prompt


def get_active_alerts() -> list[dict[str, str]]:
    return [
        {
            "id": alert_id,
            "level": "warning",
            "metric": alert_id.split("-")[0],
            "message": state["message"],
            "prompt": state["prompt"],
        }
        for alert_id, state in alert_state.items()
        if state["active"]
    ]


def monitor() -> None:
    while True:
        with lock:
            astronaut.update_health()
            current = snapshot()
            history.append(current)
            update_alert_state(current, list(history))
        sleep(UPDATE_INTERVAL)


@app.on_event("startup")
def start_monitor() -> None:
    Thread(target=monitor, daemon=True, name="astrotrack-monitor").start()


def interpret_assessment(assessment: Assessment) -> dict[str, Any]:
    symptoms = set(assessment.symptoms)
    feeling = assessment.feeling.lower()
    if "Shortness of breath" in symptoms:
        return {
            "scenario": "Possible oxygenation / breathing concern",
            "condition": "hypoxia_normal",
            "experience": "This report represents a possible breathing or oxygenation concern. The scenario may show falling blood oxygen alongside changes in heart and respiratory rate.",
            "next_steps": [
                "Tell the flight medical officer or mission control promptly.",
                "Pause strenuous activity and follow the mission's medical checklist.",
                "Confirm the reading using the approved backup measurement method.",
                "Follow real-time instructions from the medical team; do not rely on this demo for treatment.",
            ],
        }
    if "Feeling unusually warm" in symptoms or "fever" in feeling:
        return {
            "scenario": "Possible fever / infection-like pattern",
            "condition": "infection_fever",
            "experience": "This report represents a fever-like pattern. Temperature, heart rate and respiratory rate may gradually rise.",
            "next_steps": [
                "Report the symptoms and temperature trend to the flight medical officer.",
                "Recheck temperature and other readings with approved equipment.",
                "Record when symptoms began and whether they are changing.",
                "Follow the mission medical protocol and clinician instructions.",
            ],
        }
    if "Dizziness" in symptoms or "Nausea" in symptoms:
        return {
            "scenario": "Possible dehydration-like pattern",
            "condition": "dehydration",
            "experience": "This report represents a dehydration-like pattern. Heart rate and respiratory rate may rise while the simulated blood-pressure value trends downward.",
            "next_steps": [
                "Notify the flight medical officer and report the symptoms.",
                "Pause strenuous activity and use the mission's approved assessment procedure.",
                "Check recent fluid intake and associated symptoms with the medical team.",
                "Only follow hydration or other treatment instructions approved by the medical team.",
            ],
        }
    if feeling in {"unwell", "severely unwell"} or symptoms:
        return {
            "scenario": "Unclassified reported symptoms",
            "condition": None,
            "experience": "The astronaut reports not feeling well, but the selected symptoms do not match one of the demonstration scenarios. No condition is automatically assumed.",
            "next_steps": [
                "Notify the flight medical officer and describe the symptoms.",
                "Repeat the relevant measurements using approved equipment.",
                "Record symptom onset, changes and any related activity.",
                "Follow the mission medical checklist and medical-team instructions.",
            ],
        }
    return {
        "scenario": "No symptoms reported",
        "condition": None,
        "experience": "The astronaut reports feeling normal and selected no symptoms.",
        "next_steps": [
            "Continue routine monitoring.",
            "Report any new or worsening symptoms.",
        ],
    }


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse("dashboard.html")


@app.get("/api/health")
def get_health() -> dict[str, Any]:
    with lock:
        reading = snapshot()
        samples = list(history)
        alerts = get_active_alerts()
    return {
        "reading": reading,
        "status": evaluate_status(reading),
        "alerts": alerts,
        "update_interval": UPDATE_INTERVAL,
    }


@app.get("/api/history")
def get_history() -> list[dict[str, Any]]:
    with lock:
        return list(history)


@app.get("/api/astronaut")
def get_astronaut() -> dict[str, Any]:
    return {"name": astronaut.name, "age": astronaut.age}


@app.post("/api/assessment")
def submit_assessment(assessment: Assessment) -> dict[str, Any]:
    global latest_assessment, assessment_condition
    interpretation = interpret_assessment(assessment)
    with lock:
        if assessment_condition:
            astronaut.remove_condition(assessment_condition)
        assessment_condition = interpretation["condition"]
        if assessment_condition:
            astronaut.inflict_condition(assessment_condition)
        latest_assessment = {
            **assessment.model_dump(),
            "submitted_at": time(),
            **interpretation,
        }
    print("Astronaut assessment received:", latest_assessment)
    return {
        "status": "received",
        "message": "Assessment recorded.",
        "assessment": latest_assessment,
        "simulation": f"Activated {assessment_condition}"
        if assessment_condition
        else "No simulation condition activated",
    }


@app.get("/api/assessment/latest")
def get_latest_assessment() -> dict[str, Any] | None:
    return latest_assessment


@app.post("/api/condition/{condition_name}")
def activate_condition(condition_name: str) -> dict[str, str]:
    if condition_name not in astronaut.conditions:
        raise HTTPException(
            status_code=404, detail=f"Unknown condition: {condition_name}"
        )
    with lock:
        astronaut.inflict_condition(condition_name)
    return {"status": "active", "condition": condition_name}


@app.delete("/api/condition/{condition_name}")
def deactivate_condition(condition_name: str) -> dict[str, str]:
    with lock:
        astronaut.remove_condition(condition_name)
    return {"status": "removed", "condition": condition_name}
