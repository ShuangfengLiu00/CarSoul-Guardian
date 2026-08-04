"""Agent memory layer."""
from carsoul_agent.memory.base import BaseMemory, Message
from carsoul_agent.memory.conversation import ConversationMemory
from carsoul_agent.memory.episodic import EpisodicMemory, EpisodeRecord, episodic_memory
from carsoul_agent.memory.skill_memory import SkillExecutionRecord, SkillMemory, skill_memory
from carsoul_agent.memory.evolution_memory import (
    EvolutionMemory,
    EvolutionMilestone,
    evolution_memory,
)

__all__ = [
    "BaseMemory",
    "Message",
    "ConversationMemory",
    "EpisodicMemory",
    "EpisodeRecord",
    "episodic_memory",
    "SkillMemory",
    "SkillExecutionRecord",
    "skill_memory",
    "EvolutionMemory",
    "EvolutionMilestone",
    "evolution_memory",
]

# Default shared instance (single-process dev).
default_memory = ConversationMemory()
