"""Prompt management."""
from carsoul_agent.prompts.system_prompts import (
    CARSOUL_GUARDIAN_SYSTEM,
    DIAGNOSIS_SYSTEM,
    EXPLAINER_SYSTEM,
    PERCEPTION_SYSTEM,
    PROMPTS,
    PromptTemplate,
    RISK_SYSTEM,
    SERVICE_SYSTEM,
    get_prompt,
)

__all__ = [
    "CARSOUL_GUARDIAN_SYSTEM",
    "PERCEPTION_SYSTEM",
    "DIAGNOSIS_SYSTEM",
    "RISK_SYSTEM",
    "EXPLAINER_SYSTEM",
    "SERVICE_SYSTEM",
    "PROMPTS",
    "PromptTemplate",
    "get_prompt",
]
