from __future__ import annotations

from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    AgentNodeDependencies,
    auto_repair_with_pe,
    ask_for_clarification,
    build_fix_options,
    confirm_export,
    decide_need_clarification,
    decide_repair_or_continue,
    ensure_project,
    export_document,
    extract_requirements,
    match_clauses,
    render_preview,
    respond,
    understand_intent,
    validate_document,
    merge_clarifications,
)
from app.agent.state import AgentGraphState


def _route_after_ensure_project(state: AgentGraphState) -> str:
    return state.get("next_action", "respond")


def _route_after_decide_clarification(state: AgentGraphState) -> str:
    return state.get("next_action", "respond")


def _route_after_merge_clarification(state: AgentGraphState) -> str:
    return state.get("next_action", "decide_need_clarification")


def _route_after_decide_repair(state: AgentGraphState) -> str:
    return state.get("next_action", "respond")


def _route_after_render_preview(state: AgentGraphState) -> str:
    return state.get("next_action", "respond")


def _route_after_confirm_export(state: AgentGraphState) -> str:
    return state.get("next_action", "respond")


def _route_after_export(state: AgentGraphState) -> str:
    return state.get("next_action", "respond")


def build_agent_graph(
    deps: AgentNodeDependencies,
    *,
    checkpointer: Any | None = None,
    enable_interrupts: bool = True,
):
    """Build and compile the LangGraph workflow for tool-based orchestration."""

    graph = StateGraph(AgentGraphState)

    graph.add_node("understand_intent", understand_intent)
    graph.add_node("ensure_project", partial(ensure_project, deps=deps))
    graph.add_node("extract_requirements", partial(extract_requirements, deps=deps))
    graph.add_node("decide_need_clarification", decide_need_clarification)
    graph.add_node("ask_for_clarification", ask_for_clarification)
    graph.add_node("merge_clarifications", partial(merge_clarifications, deps=deps))
    graph.add_node("match_clauses", partial(match_clauses, deps=deps))
    graph.add_node("validate_document", partial(validate_document, deps=deps))
    graph.add_node("decide_repair_or_continue", decide_repair_or_continue)
    graph.add_node("auto_repair_with_pe", partial(auto_repair_with_pe, deps=deps))
    graph.add_node("build_fix_options", build_fix_options)
    graph.add_node("render_preview", partial(render_preview, deps=deps))
    graph.add_node("confirm_export", confirm_export)
    graph.add_node("export_document", partial(export_document, deps=deps))
    graph.add_node("respond", respond)

    graph.add_edge(START, "understand_intent")
    graph.add_edge("understand_intent", "ensure_project")

    graph.add_conditional_edges(
        "ensure_project",
        _route_after_ensure_project,
        {
            "extract_requirements": "extract_requirements",
            "decide_need_clarification": "decide_need_clarification",
            "respond": "respond",
        },
    )
    graph.add_edge("extract_requirements", "decide_need_clarification")
    graph.add_conditional_edges(
        "decide_need_clarification",
        _route_after_decide_clarification,
        {
            "ask_for_clarification": "ask_for_clarification",
            "merge_clarifications": "merge_clarifications",
            "match_clauses": "match_clauses",
            "respond": "respond",
        },
    )
    graph.add_edge("ask_for_clarification", "respond")
    graph.add_conditional_edges(
        "merge_clarifications",
        _route_after_merge_clarification,
        {
            "decide_need_clarification": "decide_need_clarification",
            "ask_for_clarification": "ask_for_clarification",
            "respond": "respond",
        },
    )

    graph.add_edge("match_clauses", "validate_document")
    graph.add_edge("validate_document", "decide_repair_or_continue")
    graph.add_conditional_edges(
        "decide_repair_or_continue",
        _route_after_decide_repair,
        {
            "auto_repair_with_pe": "auto_repair_with_pe",
            "build_fix_options": "build_fix_options",
            "render_preview": "render_preview",
            "respond": "respond",
        },
    )
    graph.add_edge("auto_repair_with_pe", "match_clauses")
    graph.add_edge("build_fix_options", "respond")

    graph.add_conditional_edges(
        "render_preview",
        _route_after_render_preview,
        {
            "confirm_export": "confirm_export",
            "export_document": "export_document",
            "respond": "respond",
        },
    )
    graph.add_conditional_edges(
        "confirm_export",
        _route_after_confirm_export,
        {
            "export_document": "export_document",
            "respond": "respond",
        },
    )
    graph.add_conditional_edges(
        "export_document",
        _route_after_export,
        {
            "build_fix_options": "build_fix_options",
            "respond": "respond",
        },
    )
    graph.add_edge("respond", END)

    interrupt_before = None
    if enable_interrupts:
        interrupt_before = [
            "ask_for_clarification",
            "build_fix_options",
            "confirm_export",
        ]

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
    )
