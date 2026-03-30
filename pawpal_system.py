from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Priority(Enum):
    HIGH   = 3
    MEDIUM = 2
    LOW    = 1


class TaskCategory(Enum):
    WALK       = "walk"
    FEEDING    = "feeding"
    MEDICATION = "medication"
    ENRICHMENT = "enrichment"
    GROOMING   = "grooming"
    VET_VISIT  = "vet_visit"
    PLAY       = "play"


# ---------------------------------------------------------------------------
# Core data classes
# ---------------------------------------------------------------------------

@dataclass
class CareTask:
    """A single pet care activity."""
    task_id:          str
    title:            str
    category:         TaskCategory
    duration_minutes: int
    priority:         Priority
    is_mandatory:     bool          = False
    preferred_time:   Optional[str] = None   # e.g. "08:00"
    frequency:        str           = "daily"

    def is_schedulable(self, budget: int) -> bool:
        """Return True if this task fits within the remaining time budget."""
        pass  # TODO: implement


@dataclass
class Pet:
    """The animal being cared for."""
    name:          str
    species:       str
    age:           int
    breed:         str = ""
    medical_notes: str = ""
    _tasks:        list[CareTask] = field(default_factory=list, repr=False)

    def add_task(self, task: CareTask) -> None:
        """Attach a care task to this pet."""
        pass  # TODO: implement

    def get_tasks(self) -> list[CareTask]:
        """Return all tasks assigned to this pet."""
        pass  # TODO: implement


@dataclass
class Owner:
    """The human using the app — defines time constraints and preferences."""
    name:                 str
    available_minutes:    int
    wake_time:            str        = "07:00"
    preferred_task_order: list[str]  = field(default_factory=list)
    _pets:                list[Pet]  = field(default_factory=list, repr=False)

    def add_pet(self, pet: Pet) -> None:
        """Associate a pet with this owner."""
        pass  # TODO: implement

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        pass  # TODO: implement


# ---------------------------------------------------------------------------
# Output / value objects
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    """A CareTask paired with its assigned time slot and scheduling reason."""
    task:       CareTask
    start_time: str
    end_time:   str
    reason:     str


@dataclass
class DailyPlan:
    """The final daily schedule produced by the Scheduler."""
    date:               str
    owner:              Owner
    pet:                Pet
    scheduled_tasks:    list[ScheduledTask] = field(default_factory=list)
    skipped_tasks:      list[CareTask]      = field(default_factory=list)
    total_minutes_used: int                 = 0

    def add_scheduled(self, st: ScheduledTask) -> None:
        """Add a task that made it into the plan."""
        pass  # TODO: implement

    def add_skipped(self, task: CareTask) -> None:
        """Add a task that was dropped from the plan."""
        pass  # TODO: implement

    def get_summary(self) -> str:
        """Return a short one-liner summary of the plan."""
        pass  # TODO: implement

    def get_explanation(self) -> str:
        """Return the full narrative explanation to display in the UI."""
        pass  # TODO: implement


# ---------------------------------------------------------------------------
# Scheduler — the brain of the system
# ---------------------------------------------------------------------------

class Scheduler:
    """Builds a DailyPlan for a pet based on owner constraints and task priorities."""

    def __init__(self, owner: Owner, pet: Pet) -> None:
        self.owner = owner
        self.pet   = pet

    def build_plan(self, date: str) -> DailyPlan:
        """Main entry point — sorts, fits, assigns, and returns a DailyPlan."""
        pass  # TODO: implement

    def _sort_tasks(self) -> list[CareTask]:
        """Sort tasks: mandatory first, then by priority (HIGH→LOW), then preferred_time."""
        pass  # TODO: implement

    def _fits_budget(self, task: CareTask, remaining: int) -> bool:
        """Return True if the task duration fits within remaining minutes."""
        pass  # TODO: implement

    def _assign_time(self, task: CareTask, current_time: str) -> tuple[str, str]:
        """Calculate and return (start_time, end_time) for a task."""
        pass  # TODO: implement

    def _generate_reason(self, task: CareTask) -> str:
        """Return a human-readable explanation for why this task was scheduled."""
        pass  # TODO: implement