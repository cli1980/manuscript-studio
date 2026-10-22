from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)]
ReviewerLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Note = Annotated[str, StringConstraints(max_length=10000)]
Score = Annotated[int, Field(strict=True, ge=1, le=5)]
Version = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    key: Annotated[str, StringConstraints(max_length=200)]
    rater_id: ReviewerLabel | None = None


class Submit(Input):
    version: Version


class Dimensions(Input):
    fidelity: Score | None = None
    english_naturalness: Score | None = None
    literary_voice: Score | None = None


class Issue(Input):
    dimension: Literal["fidelity", "english_naturalness", "literary_voice"]
    severity: Literal["minor", "major", "critical"]
    source_quote: Note = ""
    translation_quote: Note = ""
    explanation: Note = ""


class JudgmentCreate(Input):
    version: Version
    candidate_id: Identifier | None = None
    candidate_revision: Annotated[int, Field(strict=True, ge=1)] | None = None
    supersedes_judgment_id: Identifier | None = None
    status: Literal["pending", "complete"] = "pending"
    overall_score: Score | None = None
    dimension_scores: Dimensions = Field(default_factory=Dimensions)
    rationale: Note | None = None
    issues: Annotated[list[Issue], Field(max_length=50)] = Field(default_factory=list)
