"""CrewAI service for generating traceable user stories and acceptance criteria."""
import json, logging, os, time
from typing import Any
from crewai import Agent, Crew, LLM, Process, Task
from pydantic import BaseModel, ValidationError
from app.core.config import settings
from app.schemas.user_story import UserStoryGenerationRequest, UserStoryGenerationOutput, UserStoryGenerationResult, build_user_story_result
from app.services.token_usage import kickoff_with_token_tracking

logger = logging.getLogger(__name__)

class UserStoryGenerationError(RuntimeError):
    """Raised when user story generation fails."""

def _create_llm() -> LLM:
    if not settings.gemini_api_key:
        raise UserStoryGenerationError("Gemini API key is not configured.")
    model = (settings.gemini_model or "").strip()
    if not model:
        raise UserStoryGenerationError("Gemini model is not configured.")
    if not model.startswith("gemini/"):
        model = f"gemini/{model}"
    return LLM(model=model, api_key=settings.gemini_api_key, temperature=0.15)

def _prepare_agent_context(request: UserStoryGenerationRequest) -> dict[str, str]:
    return {"product_name": request.product_name, "prd_data": json.dumps(request.prd.model_dump(mode="json"), ensure_ascii=False)}

def _extract_output_data(result: Any) -> Any:
    structured = getattr(result, "pydantic", None)
    if isinstance(structured, BaseModel): return structured.model_dump(mode="python")
    if structured is not None: return structured
    data = getattr(result, "json_dict", None)
    if data: return data
    raw = getattr(result, "raw", None)
    if not isinstance(raw, str) or not raw.strip(): raw = str(result)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"): lines=lines[1:]
        if lines and lines[-1].strip()=="```": lines=lines[:-1]
        cleaned="\n".join(lines).strip()
    return json.loads(cleaned)

def _parse_crew_output(result: Any) -> UserStoryGenerationOutput:
    try: return UserStoryGenerationOutput.model_validate(_extract_output_data(result))
    except (ValidationError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.exception("Could not parse user story generation output.")
        raise UserStoryGenerationError("The AI returned an invalid user story response.") from exc

def _create_user_story_crew() -> Crew:
    agent = Agent(
        role="Senior Business Analyst and Agile Requirements Specialist",
        goal="Convert approved functional requirements into clear, testable, evidence-traceable user stories.",
        backstory="You are an experienced analyst. You preserve requirement intent, derive traceability from linked requirements, and never introduce unsupported product behavior.",
        llm=_create_llm(), verbose=False, allow_delegation=False,
    )
    task = Task(
        description="""Create implementation-ready user stories from the PRD.

PRODUCT: {product_name}
VALIDATED PRD: {prd_data}

RULES
1. Use the PRD as the sole source of product scope and behavior.
2. Create focused stories in the format 'As a [user], I want [capability], so that [benefit].'
3. Every story must reference one or more existing functional requirement IDs from the PRD.
4. Priority must match the linked requirement priorities. If linked requirements differ, use the highest priority in this order: Must Have, Should Have, Could Have, Won't Have.
5. Include at least one specific, observable Given-When-Then acceptance criterion per story. Include positive, negative, and boundary cases only where the PRD supports them.
6. Use unique US-001 story IDs and AC-001 criterion IDs (criterion IDs unique within each story).
7. Dependencies must reference other generated story IDs only. Avoid cycles and self-dependencies.
8. Do not invent feedback IDs. Set source_feedback_ids to the union of source_feedback_ids on the requirements referenced by the story. The backend independently recomputes this field, so treat it as traceability metadata, not a creative field.
9. Do not invent user roles, validation rules, security policies, performance targets, or implementation decisions absent from the PRD.
10. Add notes only for genuine ambiguities or stakeholder decisions.
11. Return only fields in UserStoryGenerationOutput.

Return a valid structured UserStoryGenerationOutput.""",
        expected_output="User stories with valid PRD requirement references, evidence traceability, and Given-When-Then acceptance criteria.",
        agent=agent, output_pydantic=UserStoryGenerationOutput,
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)

def _is_retryable_error(exc: Exception) -> bool:
    markers=("503","unavailable","429","resource_exhausted","rate limit","500","502","504","timeout","timed out","connection reset","temporarily unavailable")
    parts=[]; seen=set(); current=exc
    while current is not None and id(current) not in seen:
        seen.add(id(current)); parts.append(str(current).lower()); current=current.__cause__ or current.__context__
    return any(m in " ".join(parts) for m in markers) or getattr(exc,"status_code",None) in {429,500,502,503,504}

def _get_retry_settings() -> tuple[int,float]:
    try:
        attempts=int(os.getenv("USER_STORY_MAX_ATTEMPTS","3")); delay=float(os.getenv("USER_STORY_RETRY_DELAY_SECONDS","2"))
    except ValueError as exc: raise UserStoryGenerationError("Invalid user story retry configuration.") from exc
    return max(1,min(attempts,5)),max(0.0,delay)

def generate_user_stories(request: UserStoryGenerationRequest) -> UserStoryGenerationResult:
    if not request.prd.functional_requirements:
        raise UserStoryGenerationError("The supplied PRD contains no functional requirements.")
    context=_prepare_agent_context(request); attempts,delay=_get_retry_settings(); last_error=None
    for attempt in range(1,attempts+1):
        try:
            crew=_create_user_story_crew()
            raw=kickoff_with_token_tracking(crew,"user_story_generation",model=settings.gemini_model,inputs=context)
            output=_parse_crew_output(raw)
            result=build_user_story_result(request,output)
            logger.info("User stories generated | stories=%d | criteria=%d",result.total_user_stories,result.total_acceptance_criteria)
            return result
        except Exception as exc:
            last_error=exc
            if not _is_retryable_error(exc) or attempt==attempts:
                logger.exception("User Story Generation failed on attempt %d/%d",attempt,attempts); break
            time.sleep(delay*(2**(attempt-1)))
    raise UserStoryGenerationError(f"User story generation failed after {attempts} attempt(s).") from last_error
