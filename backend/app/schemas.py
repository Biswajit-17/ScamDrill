"""Pydantic schemas for scenarios and API requests/responses.

Scenario JSON files live in backend/scenarios/ and are validated with these
models on startup. The API request/response models mirror the stateless
session contract: the client holds transcript + state and sends them each
request; the server stores nothing.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


TACTIC_IDS = {
    "authority",
    "urgency",
    "fear",
    "isolation",
    "trust_building",
    "verification_blocking",
    "credential_request",
    "remote_access",
    "payment_request",
}


class Option(BaseModel):
    id: str
    text: str
    outcome: Literal["safe", "unsafe"]
    tactic: str
    feedback: str

    @model_validator(mode="after")
    def _check_tactic(self) -> "Option":
        if self.tactic not in TACTIC_IDS:
            raise ValueError(f"Unknown tactic id: {self.tactic}")
        return self


class Decision(BaseModel):
    id: str
    after_stage: str
    prompt: str
    options: List[Option]

    @model_validator(mode="after")
    def _check_unique_option_ids(self) -> "Decision":
        ids = [o.id for o in self.options]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate option ids in decision {self.id}")
        return self


class Stage(BaseModel):
    id: str
    goal: str
    tactics: List[str]
    min_turns: int = 1
    max_turns: int = 5
    fallback_lines: List[str] = []

    @model_validator(mode="after")
    def _check_tactics(self) -> "Stage":
        for t in self.tactics:
            if t not in TACTIC_IDS:
                raise ValueError(f"Unknown tactic id: {t}")
        return self


class Persona(BaseModel):
    name: str
    org: str
    role: str


class Scenario(BaseModel):
    id: str
    title: str
    persona: Persona
    stages: List[Stage]
    decisions: List[Decision]

    @model_validator(mode="after")
    def _check_stage_and_decision_ids(self) -> "Scenario":
        stage_ids = {s.id for s in self.stages}
        decision_ids = {d.id for d in self.decisions}
        if len(stage_ids) != len([s.id for s in self.stages]):
            raise ValueError(f"Duplicate stage ids in scenario {self.id}")
        if len(decision_ids) != len([d.id for d in self.decisions]):
            raise ValueError(f"Duplicate decision ids in scenario {self.id}")
        for d in self.decisions:
            if d.after_stage not in stage_ids:
                raise ValueError(
                    f"Decision {d.id} references unknown stage {d.after_stage}"
                )
        return self

    def stage_by_id(self, stage_id: str) -> Optional[Stage]:
        for s in self.stages:
            if s.id == stage_id:
                return s
        return None

    def decision_after_stage(self, stage_id: str) -> Optional[Decision]:
        for d in self.decisions:
            if d.after_stage == stage_id:
                return d
        return None


class CallerLine(BaseModel):
    message: str
    tactics: List[str]


class DebriefMoment(BaseModel):
    decision_id: str
    what_happened: str
    say_instead: str


class Debrief(BaseModel):
    summary: str
    moments: List[DebriefMoment]
    rules: List[str]


class TranscriptEntry(BaseModel):
    role: Literal["caller", "user"]
    content: str
    tactics: Optional[List[str]] = None


class CallState(BaseModel):
    scenario_id: str
    language: str = "en"
    current_stage_id: Optional[str] = None
    stage_turns: int = 0
    total_turns: int = 0
    hang_up: bool = False
    call_ended: bool = False
    transcript: List[TranscriptEntry] = []
    decisions_taken: List[dict] = []
    weak_spot_map: dict = {}
    fallback_used: bool = False
    demo_replay: bool = False


class ScenarioSummary(BaseModel):
    id: str
    title: str


class CallStartRequest(BaseModel):
    scenario_id: str
    language: str = "en"


class CallStartResponse(BaseModel):
    caller_line: str
    tactics: List[str]
    stage: str
    stage_turns: int
    decision_card: Optional[dict] = None
    call_ended: bool = False


class CallTurnRequest(BaseModel):
    state: CallState
    user_message: str


class CallTurnResponse(BaseModel):
    caller_line: str
    tactics: List[str]
    stage: str
    stage_turns: int
    decision_card: Optional[dict] = None
    call_ended: bool = False
    masked: bool = False


class DecisionRequest(BaseModel):
    state: CallState
    decision_id: str
    option_id: str


class DecisionResponse(BaseModel):
    decision_id: str
    option_id: str
    outcome: str
    tactic: str
    feedback: str
    weak_spot_map: dict
    state: CallState


class DebriefRequest(BaseModel):
    state: CallState


class DebriefResponse(BaseModel):
    summary: str
    moments: List[DebriefMoment]
    rules: List[str]
    weak_spot_map: dict
    fallback_used: bool = False