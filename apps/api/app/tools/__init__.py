"""Tool abstraction and registry.

Tools are deterministic capabilities that agents can invoke. Tool invocation
goes through a registered tool registry; the LLM is never allowed to dynamically
import arbitrary Python modules or execute arbitrary functions.
"""

from __future__ import annotations

import time
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class ToolDefinition(BaseModel):
    """Static description of a tool."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None


class ToolResult(BaseModel):
    """Result of executing a tool."""

    model_config = ConfigDict(frozen=True)

    tool_name: str
    success: bool
    output: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int | None = None


class Tool(Generic[TInput, TOutput]):
    """A typed, registered tool.

    Subclasses define :attr:`INPUT_SCHEMA` and :attr:`OUTPUT_SCHEMA` as Pydantic
    models and implement :meth:`_run`.
    """

    name: str
    description: str
    input_schema: type[TInput]
    output_schema: type[TOutput] | None

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema.model_json_schema(),
            output_schema=(
                self.output_schema.model_json_schema()
                if self.output_schema is not None
                else None
            ),
        )

    async def execute(self, input_data: Any) -> ToolResult:
        """Execute the tool with validated input and return a ToolResult."""
        start = time.perf_counter()
        try:
            # Validate input against the input schema.
            validated_input = self.input_schema.model_validate(input_data)
            output = await self._run(validated_input)
            if self.output_schema is not None:
                validated_output = self.output_schema.model_validate(output)
                output_dict = validated_output.model_dump()
            else:
                output_dict = output if isinstance(output, dict) else {"result": output}
            duration_ms = int((time.perf_counter() - start) * 1000)
            return ToolResult(
                tool_name=self.name,
                success=True,
                output=output_dict,
                duration_ms=duration_ms,
            )
        except ValidationError as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Input validation failed: {exc}",
                duration_ms=duration_ms,
            )
        except Exception as exc:  # noqa: BLE001 - surface as tool failure
            duration_ms = int((time.perf_counter() - start) * 1000)
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
            )

    async def _run(self, input_data: TInput) -> Any:
        """Actual tool logic. Subclasses override."""
        raise NotImplementedError


class ToolRegistry:
    """Central registry of tools.

    Unknown tools fail safely. Tool registration is explicit.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool[Any, Any]] = {}

    def register(self, tool: Tool[Any, Any]) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool[Any, Any] | None:
        return self._tools.get(name)

    def list(self) -> list[str]:
        return sorted(self._tools.keys())

    def definitions(self) -> list[ToolDefinition]:
        return [tool.definition() for tool in self._tools.values()]

    def has(self, name: str) -> bool:
        return name in self._tools


# Module-level default registry.
tool_registry = ToolRegistry()

__all__ = [
    "Tool",
    "ToolDefinition",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
]

from app.tools.career_tools import (  # noqa: E402,F401
    GetCareerInput,
    GetCareerOutput,
    GetCareerTool,
    ListCareersInput,
    ListCareersOutput,
    ListCareersTool,
    GetCareerRequirementsInput,
    GetCareerRequirementsOutput,
    GetCareerRequirementsTool,
    CalculateSkillMatchInput,
    CalculateSkillMatchOutput,
    CalculateSkillMatchTool,
    GetCareerRecommendationsInput,
    GetCareerRecommendationsOutput,
    GetCareerRecommendationsTool,
)
from app.tools.evidence_tools import (  # noqa: E402,F401
    GetEvidenceInput,
    GetEvidenceOutput,
    GetEvidenceTool,
    SearchEvidenceInput,
    SearchEvidenceOutput,
    SearchEvidenceTool,
    VerifyClaimInput,
    VerifyClaimOutput,
    VerifyClaimTool,
    GetClaimEvidenceInput,
    GetClaimEvidenceOutput,
    GetClaimEvidenceTool,
    build_get_evidence_tool,
    build_search_evidence_tool,
    build_verify_claim_tool,
    build_get_claim_evidence_tool,
)
from app.tools.learning_tools import (  # noqa: E402,F401
    GetLearningResourcesInput,
    GetLearningResourcesOutput,
    GetLearningResourcesTool,
    GetSkillDependenciesInput,
    GetSkillDependenciesOutput,
    GetSkillDependenciesTool,
    CalculateLearningPriorityInput,
    CalculateLearningPriorityOutput,
    CalculateLearningPriorityTool,
    GenerateLearningRoadmapInput,
    GenerateLearningRoadmapOutput,
    GenerateLearningRoadmapTool,
    GetRoadmapInput,
    GetRoadmapOutput,
    GetRoadmapTool,
    build_get_learning_resources_tool,
    build_get_skill_dependencies_tool,
    build_calculate_learning_priority_tool,
    build_generate_learning_roadmap_tool,
    build_get_roadmap_tool,
)
from app.tools.interview_tools import (  # noqa: E402,F401
    CreateInterviewSessionInput,
    CreateInterviewSessionOutput,
    CreateInterviewSessionTool,
    GetInterviewSessionInput,
    GetInterviewSessionOutput,
    GetInterviewSessionTool,
    GetNextInterviewQuestionInput,
    GetNextInterviewQuestionOutput,
    GetNextInterviewQuestionTool,
    SubmitInterviewAnswerInput,
    SubmitInterviewAnswerOutput,
    SubmitInterviewAnswerTool,
    EvaluateInterviewAnswerInput,
    EvaluateInterviewAnswerOutput,
    EvaluateInterviewAnswerTool,
    GetInterviewResultsInput,
    GetInterviewResultsOutput,
    GetInterviewResultsTool,
    build_create_interview_session_tool,
    build_get_interview_session_tool,
    build_get_next_interview_question_tool,
    build_submit_interview_answer_tool,
    build_evaluate_interview_answer_tool,
    build_get_interview_results_tool,
)
from app.tools.careertwin_tools import (  # noqa: E402,F401
    GetCareerTwinStateInput,
    GetCareerTwinStateOutput,
    GetCareerTwinStateTool,
    CalculateCareerReadinessInput,
    CalculateCareerReadinessOutput,
    CalculateCareerReadinessTool,
    GetCareerTwinInsightsInput,
    GetCareerTwinInsightsOutput,
    GetCareerTwinInsightsTool,
    GetCareerTwinConflictsInput,
    GetCareerTwinConflictsOutput,
    GetCareerTwinConflictsTool,
    GetStaleDerivedStateInput,
    GetStaleDerivedStateOutput,
    GetStaleDerivedStateTool,
    RefreshCareerTwinStateInput,
    RefreshCareerTwinStateOutput,
    RefreshCareerTwinStateTool,
    build_get_careertwin_state_tool,
    build_calculate_career_readiness_tool,
    build_get_careertwin_insights_tool,
    build_get_careertwin_conflicts_tool,
    build_get_stale_derived_state_tool,
    build_refresh_careertwin_state_tool,
)
