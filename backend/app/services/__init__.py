"""Service layer — full vehicle digital-life archive (TASK007 + V2).

Services orchestrate business logic and delegate AI calls to the
`carsoul_agent` package. No AI/LLM logic lives in the API routes.
"""
from app.services import (
    agent_service,
    alert_service,
    data_generator,
    digital_state_service,
    digital_twin_service,
    driving_behavior_service,
    fault_log_service,
    health_score_service,
    health_service,
    knowledge_service,
    lifecycle_generator,
    lifecycle_service,
    maintenance_service,
    ownership_service,
    risk_prediction_service,
    sensor_data_service,
    service_order_service,
    soul_engine_service,
    trip_service,
    user_service,
    vehicle_life_service,
    vehicle_service,
)

__all__ = [
    "agent_service",
    "alert_service",
    "data_generator",
    "digital_state_service",
    "digital_twin_service",
    "driving_behavior_service",
    "fault_log_service",
    "health_score_service",
    "health_service",
    "knowledge_service",
    "lifecycle_generator",
    "lifecycle_service",
    "maintenance_service",
    "ownership_service",
    "risk_prediction_service",
    "sensor_data_service",
    "service_order_service",
    "soul_engine_service",
    "trip_service",
    "user_service",
    "vehicle_life_service",
    "vehicle_service",
]
