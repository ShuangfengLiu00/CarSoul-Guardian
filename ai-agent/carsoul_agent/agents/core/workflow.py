"""LangGraph-style state machine for the CarSoul Core Agent workflow.

This is a **pure-Python** directed graph that mirrors LangGraph's API
(``add_node`` / ``add_edge`` / ``add_conditional_edges`` / ``compile``)
so the system works offline without the ``langgraph`` dependency. If
``langgraph`` is installed it can be swapped in transparently later; the
node functions and state contract are identical.

Graph topology (from technical design §3):

    START
      │
      ▼
    perception ──────{ is_normal? }
      │                      │
      │              false ──┤── true
      │                      │       │
      ▼                      ▼       ▼
    diagnosis            ┌─ explainer ─┐
      │                  │      │      │
      ▼                  │      ▼      │
     risk                │   service   │
      │                  │      │      │
      ▼                  │      ▼      │
    explainer ───────────┘     END     │
      │                              │
      ▼                              │
    service ─────────────────────────┘
      │
      ▼
    END

Every node appends to ``state["trace_log"]``, so the compiled graph's
output is fully replayable — the "推理可追溯" criterion.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from carsoul_agent.agents.core.diagnosis import DiagnosisAgent
from carsoul_agent.agents.core.explainer import ExplainerAgent
from carsoul_agent.agents.core.perception import PerceptionAgent
from carsoul_agent.agents.core.risk import RiskAgent
from carsoul_agent.agents.core.service import ServiceAgent
from carsoul_agent.agents.core.state import AgentState, trace_entry
from carsoul_agent.config import settings

logger = logging.getLogger(__name__)

# Sentinel for the terminal node.
_END = "__end__"


class StateGraph:
    """A minimal directed graph with conditional routing.

    Mirrors the subset of LangGraph's ``StateGraph`` API that CarSoul
    needs: nodes, static edges, one conditional fork, and a compiled
    runner. Keeping it dependency-free guarantees offline demo works.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Callable[[AgentState], AgentState]] = {}
        self._edges: dict[str, str] = {}  # static: source -> target
        self._conditionals: dict[str, tuple[Callable, dict[str, str]]] = {}
        self._entry: str | None = None

    def add_node(self, name: str, fn: Callable[[AgentState], AgentState]) -> "StateGraph":
        self._nodes[name] = fn
        return self

    def add_edge(self, source: str, target: str) -> "StateGraph":
        self._edges[source] = target
        return self

    def add_conditional_edges(
        self,
        source: str,
        condition: Callable[[AgentState], str],
        mapping: dict[str, str],
    ) -> "StateGraph":
        self._conditionals[source] = (condition, mapping)
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        self._entry = name
        return self

    def compile(self) -> "CompiledGraph":
        if self._entry is None:
            raise ValueError("Entry point not set")
        return CompiledGraph(
            nodes=self._nodes,
            edges=self._edges,
            conditionals=self._conditionals,
            entry=self._entry,
        )


class CompiledGraph:
    """Runnable produced by ``StateGraph.compile()``."""

    def __init__(
        self,
        nodes: dict,
        edges: dict,
        conditionals: dict,
        entry: str,
    ) -> None:
        self._nodes = nodes
        self._edges = edges
        self._conditionals = conditionals
        self._entry = entry

    def invoke(self, state: AgentState) -> AgentState:
        """Execute the graph to completion, returning the final state."""
        # Ensure trace_log exists.
        if "trace_log" not in state:
            state["trace_log"] = []

        current = self._entry
        visited: list[str] = []
        max_steps = 20  # safety guard against infinite loops

        while current != _END and max_steps > 0:
            max_steps -= 1
            if current not in self._nodes:
                logger.warning("Graph reached unknown node '%s', stopping.", current)
                break

            fn = self._nodes[current]
            visited.append(current)
            logger.debug("Graph node: %s", current)
            state = fn(state)

            # Determine next node.
            if current in self._conditionals:
                cond_fn, mapping = self._conditionals[current]
                branch = cond_fn(state)
                current = mapping.get(branch, _END)
            elif current in self._edges:
                current = self._edges[current]
            else:
                current = _END

        # Append a final trace summary.
        state["trace_log"].append(trace_entry(
            step="__complete__",
            agent="workflow",
            detail=f"工作流完成，经过 {len(visited)} 个节点：{' → '.join(visited)}",
            data={"path": visited},
        ))
        return state


# ------------------------------------------------------------------ #
#  Graph construction
# ------------------------------------------------------------------ #
def _route_after_perception(state: AgentState) -> str:
    """Conditional router: normal report vs full diagnosis chain."""
    return "normal" if state.get("is_normal", False) else "anomaly"


def build_core_workflow(
    llm_client: Any | None = None,
    model_name: str | None = None,
) -> CompiledGraph:
    """Build and compile the five-sub-agent workflow graph.

    Args:
        llm_client: Optional OpenAI-compatible client. When ``None`` the
            sub-agents run in rule-based offline mode.
        model_name: LLM model name (defaults to settings).

    Returns:
        A ``CompiledGraph`` ready to ``.invoke(state)``.
    """
    model = model_name or settings.model_name

    # Instantiate the five sub-agents.
    perception = PerceptionAgent(llm_client=llm_client, model_name=model)
    diagnosis = DiagnosisAgent(llm_client=llm_client, model_name=model)
    risk = RiskAgent(llm_client=llm_client, model_name=model)
    explainer = ExplainerAgent(llm_client=llm_client, model_name=model)
    service = ServiceAgent(llm_client=llm_client, model_name=model)

    graph = StateGraph()
    graph.set_entry_point("perception")

    # Register nodes.
    graph.add_node("perception", perception.run)
    graph.add_node("diagnosis", diagnosis.run)
    graph.add_node("risk", risk.run)
    graph.add_node("explainer", explainer.run)
    graph.add_node("service", service.run)

    # Conditional fork after perception.
    graph.add_conditional_edges(
        "perception",
        _route_after_perception,
        {
            "normal": "explainer",   # skip diagnosis/risk
            "anomaly": "diagnosis",  # full chain
        },
    )

    # Anomaly branch: diagnosis → risk → explainer → service → END.
    graph.add_edge("diagnosis", "risk")
    graph.add_edge("risk", "explainer")
    graph.add_edge("explainer", "service")
    graph.add_edge("service", _END)

    return graph.compile()


class CoreWorkflow:
    """Convenience wrapper around the compiled graph.

    Provides a simple ``run(state)`` method and caches the compiled
    graph so it is only built once per process.
    """

    _graph: CompiledGraph | None = None
    _llm_client: Any | None = None
    _model_name: str | None = None

    @classmethod
    def configure(cls, llm_client: Any | None = None, model_name: str | None = None) -> None:
        """Set the LLM client and rebuild the graph on next ``run``."""
        cls._llm_client = llm_client
        cls._model_name = model_name
        cls._graph = None

    @classmethod
    def get_graph(cls) -> CompiledGraph:
        if cls._graph is None:
            cls._graph = build_core_workflow(
                llm_client=cls._llm_client,
                model_name=cls._model_name,
            )
        return cls._graph

    @classmethod
    def run(cls, state: AgentState) -> AgentState:
        """Execute the five-sub-agent workflow on the given state."""
        return cls.get_graph().invoke(state)
