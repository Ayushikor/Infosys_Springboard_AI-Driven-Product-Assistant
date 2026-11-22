"""
CrewAI service for the User Story and Acceptance Criteria Agent.

Consumes:
- Generated PRD from the PRD Generation Agent
- Functional requirements
- Target users
- Feature scope and objectives

Produces:
- Structured user stories
- Given-When-Then acceptance criteria
- Story dependencies
- Generation notes
"""

import json
import logging
import os
import time
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from pydantic import BaseModel, ValidationError

from app.core.config import settings

from app.schemas.user_story import (
    UserStoryGenerationRequest,
    UserStoryGenerationOutput,
    UserStoryGenerationResult,
    build_user_story_result,
)

from app.services.token_usage import kickoff_with_token_tracking


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# CUSTOM EXCEPTION
# ---------------------------------------------------------


class UserStoryGenerationError(RuntimeError):
    """Raised when user story generation fails."""


# ---------------------------------------------------------
# GEMINI CONFIGURATION
# ---------------------------------------------------------


def _create_llm() -> LLM:
    """Create the Gemini LLM used by the CrewAI agent."""

    api_key = settings.gemini_api_key
    configured_model = settings.gemini_model

    if not api_key:
        raise UserStoryGenerationError(
            "Gemini API key is not configured."
        )

    if not configured_model or not configured_model.strip():
        raise UserStoryGenerationError(
            "Gemini model is not configured."
        )

    model_name = configured_model.strip()

    if not model_name.startswith("gemini/"):
        model_name = f"gemini/{model_name}"

    return LLM(
        model=model_name,
        api_key=api_key,
        temperature=0.2,
    )


# ---------------------------------------------------------
# PREPARE PRD CONTEXT
# ---------------------------------------------------------


def _prepare_agent_context(
    request: UserStoryGenerationRequest,
) -> dict[str, str]:
    """Convert the PRD into structured context for Gemini."""

    return {
        "product_name": request.product_name,
        "prd_data": json.dumps(
            request.prd.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }


# ---------------------------------------------------------
# EXTRACT CREWAI OUTPUT
# ---------------------------------------------------------


def _extract_output_data(result: Any) -> Any:
    """Extract structured output from CrewAI."""

    structured_output = getattr(
        result,
        "pydantic",
        None,
    )

    if isinstance(structured_output, BaseModel):
        return structured_output.model_dump(mode="python")

    if structured_output is not None:
        return structured_output

    json_output = getattr(
        result,
        "json_dict",
        None,
    )

    if json_output:
        return json_output

    raw_output = getattr(
        result,
        "raw",
        None,
    )

    if not isinstance(raw_output, str) or not raw_output.strip():
        raw_output = str(result)

    cleaned = raw_output.strip()

    # Remove Markdown JSON code fences if present.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    return json.loads(cleaned)


# ---------------------------------------------------------
# VALIDATE CREWAI OUTPUT
# ---------------------------------------------------------


def _parse_crew_output(
    result: Any,
) -> UserStoryGenerationOutput:
    """Parse and validate Gemini's structured response."""

    try:
        raw_data = _extract_output_data(result)

        return UserStoryGenerationOutput.model_validate(
            raw_data
        )

    except (
        ValidationError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:

        logger.exception(
            "Could not parse user story generation output."
        )

        raise UserStoryGenerationError(
            "The AI returned an invalid user story response."
        ) from exc


# ---------------------------------------------------------
# CREATE AGENT AND TASK
# ---------------------------------------------------------


def _create_user_story_crew() -> Crew:
    """Create the User Story Generation Agent crew."""

    llm = _create_llm()

    agent = Agent(
        role="Senior Business Analyst and Agile Requirements Specialist",

        goal=(
            "Transform approved product requirements into clear, "
            "testable user stories with measurable acceptance "
            "criteria and valid dependencies."
        ),

        backstory=(
            "You are an experienced business analyst and Agile "
            "requirements specialist. You translate product "
            "requirements into user-focused stories that developers "
            "and QA engineers can understand and implement. "
            "You write precise Given-When-Then acceptance criteria "
            "and never introduce requirements that are absent "
            "from the supplied PRD."
        ),

        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    task = Task(
        description="""
You are the User Story and Acceptance Criteria Agent.

Your responsibility is to convert the supplied Product Requirements
Document into implementation-ready user stories.

PRODUCT NAME:
{product_name}

APPROVED PRODUCT REQUIREMENTS DOCUMENT:
{prd_data}


=========================================================
PART A - UNDERSTAND THE PRD
=========================================================

1. Read the entire PRD.
2. Understand its problem statement and proposed solution.
3. Review the functional requirements.
4. Review the target users.
5. Review the feature scope and objectives.
6. Review dependencies and assumptions.
7. Use the PRD as the source of truth.

Do not introduce functionality that is not supported by the PRD.


=========================================================
PART B - GENERATE USER STORIES
=========================================================

Create meaningful user stories for the functional requirements.

Use this standard format:

"As a [user type], I want [capability], so that [benefit]."

Every story must contain:

- story_id
- title
- user_type
- user_story
- requirement_ids
- priority
- acceptance_criteria
- dependencies
- notes

Use unique story IDs:

US-001
US-002
US-003

Each story must reference one or more valid functional requirement IDs
from the supplied PRD.

A functional requirement may be represented by multiple user stories
when it contains multiple independently testable capabilities.

Do not create duplicate stories for the same behavior.

Keep stories focused and independently understandable.


=========================================================
PART C - USER TYPES
=========================================================

Use the target users identified in the PRD.

For each story:

- Identify the appropriate user role.
- Describe the capability from that user's perspective.
- Explain the benefit of the capability.

Do not invent user roles that are unrelated to the PRD.

If a precise role is unavailable, use a reasonable generic user type
supported by the PRD.


=========================================================
PART D - PRIORITY
=========================================================

Use the priority of the related PRD functional requirements.

Allowed values:

- Must Have
- Should Have
- Could Have
- Won't Have

Do not invent a different priority system.

If a story references multiple requirements with different priorities,
use the highest applicable priority in this order:

Must Have
Should Have
Could Have
Won't Have


=========================================================
PART E - ACCEPTANCE CRITERIA
=========================================================

Every user story must contain at least one acceptance criterion.

Write acceptance criteria using:

GIVEN:
The initial condition or context.

WHEN:
The action performed by the user or system.

THEN:
The expected observable result.

Each criterion must contain:

- criterion_id
- given
- when
- then

Use unique criterion IDs within each story:

AC-001
AC-002
AC-003

Acceptance criteria must be:

1. Specific.
2. Testable.
3. Unambiguous.
4. Relevant to the user story.
5. Consistent with the PRD.

Include relevant positive, negative and boundary scenarios
where the PRD provides enough information.

Do not invent technical behavior, validation rules or business
policies that are not established in the PRD.

Avoid vague statements such as:

- The system should work properly.
- The feature should be user-friendly.
- The application should be fast.

Describe observable outcomes instead.


=========================================================
PART F - STORY DEPENDENCIES
=========================================================

Identify dependencies between generated user stories.

Use story IDs in the dependencies field.

Only add a dependency when another story genuinely needs to be
completed first.

Do not create circular dependencies.

Do not make a story depend on itself.

Use an empty list when no dependency exists.


=========================================================
PART G - NOTES
=========================================================

Add implementation or clarification notes only when useful.

Notes may identify:

- Unresolved product decisions.
- Ambiguous requirements.
- Important assumptions.
- Clarifications required from stakeholders.

Do not present assumptions as confirmed functionality.


=========================================================
FINAL VALIDATION
=========================================================

Before returning the output:

1. Verify every story references valid PRD requirement IDs.
2. Verify every story has acceptance criteria.
3. Verify all story IDs are unique.
4. Verify criterion IDs are unique within each story.
5. Verify dependencies reference existing story IDs.
6. Verify no story depends on itself.
7. Verify the acceptance criteria are testable.
8. Verify no unsupported functionality has been introduced.
9. Verify all priority values match the permitted values.
10. Return only fields defined in UserStoryGenerationOutput.

Return a valid structured UserStoryGenerationOutput.
""",

        expected_output=(
            "A structured collection of user stories with unique IDs, "
            "valid PRD requirement references, priorities, "
            "Given-When-Then acceptance criteria, dependencies "
            "and generation notes."
        ),

        agent=agent,
        output_pydantic=UserStoryGenerationOutput,
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


# ---------------------------------------------------------
# RETRY HELPERS
# ---------------------------------------------------------


def _is_retryable_error(exc: Exception) -> bool:
    """Identify temporary Gemini or API errors."""

    error_parts = []
    current = exc
    visited = set()

    while current is not None and id(current) not in visited:

        visited.add(id(current))
        error_parts.append(str(current).lower())

        current = (
            current.__cause__
            or current.__context__
        )

    message = " ".join(error_parts)

    retryable_markers = (
        "503",
        "unavailable",
        "429",
        "resource_exhausted",
        "rate limit",
        "too many requests",
        "500",
        "502",
        "504",
        "timed out",
        "timeout",
        "connection reset",
        "temporarily unavailable",
        "temporary failure",
    )

    if any(
        marker in message
        for marker in retryable_markers
    ):
        return True

    status_code = getattr(
        exc,
        "status_code",
        None,
    )

    return status_code in {
        429,
        500,
        502,
        503,
        504,
    }


def _get_retry_settings() -> tuple[int, float]:
    """Read retry configuration from environment variables."""

    try:
        max_attempts = int(
            os.getenv(
                "USER_STORY_MAX_ATTEMPTS",
                "3",
            )
        )

        retry_delay = float(
            os.getenv(
                "USER_STORY_RETRY_DELAY_SECONDS",
                "2",
            )
        )

    except ValueError as exc:
        raise UserStoryGenerationError(
            "Invalid user story retry configuration."
        ) from exc

    return (
        max(1, min(max_attempts, 5)),
        max(0.0, retry_delay),
    )


# ---------------------------------------------------------
# MAIN USER STORY GENERATION EXECUTION
# ---------------------------------------------------------


def generate_user_stories(
    request: UserStoryGenerationRequest,
) -> UserStoryGenerationResult:
    """
    Generate user stories and acceptance criteria from a PRD.

    Input:
        Product name and validated PRD.

    Output:
        Validated user stories with acceptance criteria.
    """

    if not request.prd.functional_requirements:
        raise UserStoryGenerationError(
            "The supplied PRD contains no functional requirements."
        )

    try:

        # -------------------------------------------------
        # PREPARE INPUT CONTEXT
        # -------------------------------------------------

        context = _prepare_agent_context(request)

        logger.info(
            "User Story Generation started for product '%s'.",
            request.product_name,
        )

        # -------------------------------------------------
        # RETRY CONFIGURATION
        # -------------------------------------------------

        max_attempts, retry_delay = _get_retry_settings()

        last_error = None

        # -------------------------------------------------
        # EXECUTE CREWAI AGENT
        # -------------------------------------------------

        for attempt in range(1, max_attempts + 1):

            try:

                crew = _create_user_story_crew()

                crew_result = kickoff_with_token_tracking(
                    crew,
                    "user_story_generation",
                    model=settings.gemini_model,
                    inputs=context,
                )

                # Parse and validate Gemini output.
                output = _parse_crew_output(
                    crew_result
                )

                # Validate references against the original PRD.
                final_result = build_user_story_result(
                    request=request,
                    output=output,
                )

                logger.info(
                    "User Story Generation completed. "
                    "Stories: %d | Acceptance criteria: %d",
                    final_result.total_user_stories,
                    final_result.total_acceptance_criteria,
                )

                return final_result

            except Exception as exc:

                last_error = exc

                retryable = _is_retryable_error(exc)

                if not retryable or attempt >= max_attempts:

                    logger.exception(
                        "User Story Generation failed on attempt %d/%d.",
                        attempt,
                        max_attempts,
                    )

                    break

                delay = retry_delay * (2 ** (attempt - 1))

                logger.warning(
                    "User Story Generation attempt %d/%d failed "
                    "with a temporary error. Retrying in %.1f seconds. "
                    "Error: %s",
                    attempt,
                    max_attempts,
                    delay,
                    exc,
                )

                if delay:
                    time.sleep(delay)

        raise UserStoryGenerationError(
            f"User story generation failed after {max_attempts} attempt(s)."
        ) from last_error

    except UserStoryGenerationError:
        raise

    except Exception as exc:

        logger.exception(
            "Unexpected user story generation failure."
        )

        raise UserStoryGenerationError(
            "User stories could not be generated."
        ) from exc