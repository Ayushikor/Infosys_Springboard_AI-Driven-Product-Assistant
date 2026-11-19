"""Backend-only, provider-reported token usage tracking.

This module reads usage counters returned by CrewAI or Google Gen AI.
It never estimates tokens from prompt/response text length.
"""

import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Mapping

logger = logging.getLogger(__name__)

_ACTIVE_RUN: ContextVar["TokenUsageRun | None"] = ContextVar(
    "active_token_usage_run", default=None
)


def _to_dict(value: Any) -> dict:
    """Convert SDK or Pydantic usage objects into a dictionary."""

    if value is None:
        return {}

    if isinstance(value, Mapping):
        return dict(value)

    if hasattr(value, "model_dump"):
        try:
            result = value.model_dump()
            if isinstance(result, Mapping):
                return dict(result)
        except Exception:
            logger.debug(
                "Could not convert usage model.",
                exc_info=True,
            )

    names = (
        "prompt_tokens",
        "input_tokens",
        "prompt_token_count",
        "completion_tokens",
        "output_tokens",
        "candidates_token_count",
        "total_tokens",
        "total_token_count",
        "successful_requests",
        "requests",
    )

    return {
        name: getattr(value, name)
        for name in names
        if hasattr(value, name)
    }


def _number(data: dict, *keys: str):
    """Return the first valid non-negative integer."""

    for key in keys:
        value = data.get(key)

        if value is None or isinstance(value, bool):
            continue

        try:
            value = int(value)
        except (TypeError, ValueError, OverflowError):
            continue

        if value >= 0:
            return value

    return None


def normalize_usage(raw: Any) -> dict:
    """Normalize CrewAI and Gemini usage metadata."""

    data = _to_dict(raw)

    input_tokens = _number(
        data,
        "prompt_tokens",
        "input_tokens",
        "prompt_token_count",
    )

    output_tokens = _number(
        data,
        "completion_tokens",
        "output_tokens",
        "candidates_token_count",
    )

    total_tokens = _number(
        data,
        "total_tokens",
        "total_token_count",
    )

    requests = _number(
        data,
        "successful_requests",
        "requests",
    )

    # Derive total only when both exact provider-reported
    # input and output counts are available.
    if (
        total_tokens is None
        and input_tokens is not None
        and output_tokens is not None
    ):
        total_tokens = input_tokens + output_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "successful_requests": requests,
    }


class TokenUsageRun:

    def __init__(self, name: str):
        self.name = name
        self.by_agent: dict[str, dict] = {}

    def add(
        self,
        agent: str,
        raw: Any,
        source: str,
        model: str | None,
    ):
        usage = normalize_usage(raw)

        row = self.by_agent.setdefault(
            agent,
            {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "successful_requests": None,
                "measured_calls": 0,
                "unmeasured_calls": 0,
                "sources": [],
                "model": model,
            },
        )

        for key in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "successful_requests",
        ):
            value = usage[key]

            if value is not None:
                row[key] = (row[key] or 0) + value

        if any(
            usage[key] is not None
            for key in (
                "input_tokens",
                "output_tokens",
                "total_tokens",
            )
        ):
            row["measured_calls"] += 1
        else:
            row["unmeasured_calls"] += 1

        if source not in row["sources"]:
            row["sources"].append(source)

        logger.info(
            "TOKEN_USAGE agent=%s model=%s input=%s "
            "output=%s total=%s requests=%s source=%s",
            agent,
            model or "unknown",
            usage["input_tokens"],
            usage["output_tokens"],
            usage["total_tokens"],
            usage["successful_requests"],
            source,
        )

    def report(self) -> dict:

        def total(key):
            values = [
                row[key]
                for row in self.by_agent.values()
                if row[key] is not None
            ]

            return sum(values) if values else None

        measured = sum(
            row["measured_calls"]
            for row in self.by_agent.values()
        )

        unmeasured = sum(
            row["unmeasured_calls"]
            for row in self.by_agent.values()
        )

        return {
            "run": self.name,
            "measurement": "provider_reported_usage_only",
            "input_tokens": total("input_tokens"),
            "output_tokens": total("output_tokens"),
            "total_tokens": total("total_tokens"),
            "successful_requests": total("successful_requests"),
            "measured_calls": measured,
            "unmeasured_calls": unmeasured,
            "complete": measured > 0 and unmeasured == 0,
            "by_agent": self.by_agent,
        }


def record_usage(
    agent: str,
    raw: Any,
    *,
    source: str,
    model: str | None = None,
):
    """Record token usage in the active run or backend logs."""

    run = _ACTIVE_RUN.get()

    if run is not None:
        run.add(agent, raw, source, model)
    else:
        usage = normalize_usage(raw)

        logger.info(
            "TOKEN_USAGE agent=%s model=%s input=%s "
            "output=%s total=%s source=%s",
            agent,
            model or "unknown",
            usage["input_tokens"],
            usage["output_tokens"],
            usage["total_tokens"],
            source,
        )


def kickoff_with_token_tracking(
    crew: Any,
    agent: str,
    *,
    model: str | None = None,
    **kwargs,
):
    """Execute a CrewAI crew and capture its usage metadata."""

    try:
        output = crew.kickoff(**kwargs)

    except Exception:
        # A failed kickoff may still have made provider calls.
        # Check whether CrewAI retained its usage metrics.
        raw = getattr(crew, "usage_metrics", None)

        record_usage(
            agent,
            raw,
            source="crewai.usage_metrics_after_error",
            model=model,
        )

        raise

    raw = getattr(output, "token_usage", None)
    source = "crewai_output.token_usage"

    usage = normalize_usage(raw)

    if all(
        usage[key] is None
        for key in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
        )
    ):
        fallback = getattr(crew, "usage_metrics", None)

        if fallback is not None:
            raw = fallback
            source = "crewai.usage_metrics"

    record_usage(
        agent,
        raw,
        source=source,
        model=model,
    )

    return output


def record_google_genai_usage(
    agent: str,
    usage_metadata: Any,
    *,
    model: str | None = None,
):
    """Capture token counts returned by the Google Gen AI SDK."""

    record_usage(
        agent,
        usage_metadata,
        source="google_genai.response.usage_metadata",
        model=model,
    )


@contextmanager
def capture_token_usage(
    name: str,
) -> Iterator[TokenUsageRun]:
    """Aggregate usage for one backend operation."""

    run = TokenUsageRun(name)

    token = _ACTIVE_RUN.set(run)

    try:
        yield run

    finally:
        _ACTIVE_RUN.reset(token)

        logger.info(
            "TOKEN_USAGE_SUMMARY %s",
            json.dumps(
                run.report(),
                separators=(",", ":"),
                sort_keys=True,
            ),
        )