from __future__ import annotations
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
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
    """A single pet care activity with duration, priority, recurrence, and completion state."""

    task_id:          str
    title:            str
    category:         TaskCategory
    duration_minutes: int
    priority:         Priority
    is_mandatory:     bool          = False
    preferred_time:   Optional[str] = None    # e.g. "08:00"
    frequency:        str           = "daily" # "daily" | "weekly" | "once"
    completed:        bool          = False
    due_date:         Optional[str] = None    # e.g. "2026-03-29"

    def is_schedulable(self, budget: int) -> bool:
        """Return True if this task fits within the remaining time budget."""
        return self.duration_minutes <= budget

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def next_occurrence(self, from_date: str) -> CareTask:
        """Return a new CareTask for the next recurrence based on frequency.

        Uses Python's timedelta to calculate the next due date:
          - daily  -> from_date + 1 day
          - weekly -> from_date + 7 days
          - once   -> no recurrence; returns None
        """
        if self.frequency == "once":
            return None  # non-recurring tasks do not repeat

        base = datetime.strptime(from_date, "%Y-%m-%d")
        delta = timedelta(weeks=1) if self.frequency == "weekly" else timedelta(days=1)
        next_date = (base + delta).strftime("%Y-%m-%d")

        # dataclasses.replace() creates a shallow copy with specified fields overridden
        return replace(
            self,
            task_id   = f"{self.task_id}_r",
            completed = False,
            due_date  = next_date,
        )


@dataclass
class Pet:
    """The animal being cared for; owns a list of care tasks."""

    name:          str
    species:       str
    age:           int
    breed:         str = ""
    medical_notes: str = ""
    _tasks:        list[CareTask] = field(default_factory=list, repr=False, init=False)

    def add_task(self, task: CareTask) -> None:
        """Attach a care task to this pet."""
        self._tasks.append(task)

    def get_tasks(self) -> list[CareTask]:
        """Return a copy of all tasks assigned to this pet."""
        return list(self._tasks)


@dataclass
class Owner:
    """The human user; defines the time budget, wake time, and owns the pets."""

    name:                 str
    available_minutes:    int
    wake_time:            str       = "07:00"
    preferred_task_order: list[str] = field(default_factory=list)
    _pets:                list[Pet] = field(default_factory=list, repr=False, init=False)

    def add_pet(self, pet: Pet) -> None:
        """Associate a pet with this owner."""
        self._pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        return list(self._pets)

    def get_all_tasks(self) -> list[tuple[Pet, CareTask]]:
        """Return every (pet, task) pair across all pets — used by the Scheduler."""
        return [
            (pet, task)
            for pet in self._pets
            for task in pet.get_tasks()
        ]

    def filter_tasks_by_pet(self, pet_name: str) -> list[CareTask]:
        """Return all tasks that belong to the pet matching pet_name (case-insensitive)."""
        for pet in self._pets:
            if pet.name.lower() == pet_name.lower():
                return pet.get_tasks()
        return []


# ---------------------------------------------------------------------------
# Output / value objects
# ---------------------------------------------------------------------------

@dataclass
class SkippedTask:
    """A CareTask that could not be scheduled, paired with the reason why."""

    task:   CareTask
    reason: str


@dataclass
class ScheduledTask:
    """A CareTask placed on the timeline with a start/end time and scheduling reason."""

    task:       CareTask
    start_time: str
    end_time:   str
    reason:     str


@dataclass
class DailyPlan:
    """The complete daily schedule produced by the Scheduler."""

    date:               str
    owner:              Owner
    pet:                Pet
    scheduled_tasks:    list[ScheduledTask] = field(default_factory=list)
    skipped_tasks:      list[SkippedTask]   = field(default_factory=list)
    total_minutes_used: int                 = 0
    conflicts:          list[str]           = field(default_factory=list)  # conflict warnings

    def add_scheduled(self, st: ScheduledTask) -> None:
        """Add a task that made it into the plan and update the minutes counter."""
        self.scheduled_tasks.append(st)
        self.total_minutes_used += st.task.duration_minutes

    def add_skipped(self, st: SkippedTask) -> None:
        """Add a task that was dropped from the plan."""
        self.skipped_tasks.append(st)

    def get_summary(self) -> str:
        """Return a short one-liner overview of the plan."""
        n_sched = len(self.scheduled_tasks)
        n_skip  = len(self.skipped_tasks)
        budget  = self.owner.available_minutes
        return (
            f"{n_sched} task(s) scheduled "
            f"({self.total_minutes_used} min used of {budget} min available). "
            f"{n_skip} task(s) skipped."
        )

    def get_explanation(self) -> str:
        """Return the full narrative plan explanation for the UI or terminal."""
        lines = [
            f"Daily Plan for {self.pet.name}  |  {self.date}",
            "=" * 50,
            self.get_summary(),
        ]

        if self.conflicts:
            lines.append("\nCONFLICT WARNINGS:")
            for c in self.conflicts:
                lines.append(f"  !! {c}")

        if self.scheduled_tasks:
            lines.append("\nSCHEDULED TASKS:")
            for entry in self.scheduled_tasks:
                badge = "[MANDATORY] " if entry.task.is_mandatory else ""
                lines.append(
                    f"  {entry.start_time} to {entry.end_time}  "
                    f"{badge}{entry.task.title}  ({entry.task.duration_minutes} min)"
                )
                lines.append(f"    >> {entry.reason}")

        if self.skipped_tasks:
            lines.append("\nSKIPPED TASKS:")
            for sk in self.skipped_tasks:
                lines.append(f"  SKIPPED: {sk.task.title} - {sk.reason}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scheduler — the brain of the system
# ---------------------------------------------------------------------------

class Scheduler:
    """Builds a DailyPlan for a single pet based on the owner's time constraints."""

    _TIME_FMT = "%H:%M"
    _DATE_FMT = "%Y-%m-%d"

    def __init__(self, owner: Owner, pet: Pet) -> None:
        """Initialise the scheduler with an owner (constraints) and a pet (tasks)."""
        self.owner = owner
        self.pet   = pet

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_plan(self, date: str) -> DailyPlan:
        """Sort, fit, and time-assign all pending tasks; run conflict detection; return DailyPlan."""
        plan         = DailyPlan(date=date, owner=self.owner, pet=self.pet)
        remaining    = self.owner.available_minutes
        current_time = self.owner.wake_time

        # Only schedule tasks that are not already completed
        pending = self.filter_by_status(self._sort_tasks(), completed=False)

        for task in pending:
            if self._fits_budget(task, remaining):
                start, end = self._assign_time(task, current_time)
                reason     = self._generate_reason(task)
                plan.add_scheduled(ScheduledTask(
                    task=task, start_time=start, end_time=end, reason=reason
                ))
                remaining   -= task.duration_minutes
                current_time = end
            else:
                reason = (
                    f"Only {remaining} min remaining; "
                    f"this task needs {task.duration_minutes} min"
                )
                plan.add_skipped(SkippedTask(task=task, reason=reason))

        # Run conflict detection automatically after scheduling
        plan.conflicts = self.detect_conflicts(plan.scheduled_tasks)
        return plan

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    @staticmethod
    def sort_by_time(tasks: list[CareTask]) -> list[CareTask]:
        """Sort tasks by preferred_time (HH:MM) ascending using a lambda key.

        Tasks without a preferred_time are sorted to the end.
        The lambda uses "23:59" as a sentinel for tasks with no preference,
        which is a simple and readable way to push them to the bottom.
        """
        return sorted(tasks, key=lambda t: t.preferred_time or "23:59")

    def _sort_tasks(self) -> list[CareTask]:
        """Sort tasks: mandatory first, then priority HIGH->LOW, then preferred_time."""
        return sorted(
            self.pet.get_tasks(),
            key=lambda t: (
                not t.is_mandatory,
                -t.priority.value,
                t.preferred_time or "23:59",
            ),
        )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    @staticmethod
    def filter_by_status(tasks: list[CareTask], completed: bool) -> list[CareTask]:
        """Filter a task list by completion status.

        Pass completed=True to get finished tasks, False to get pending ones.
        Uses a list comprehension — the most readable Pythonic approach for simple filters.
        """
        return [t for t in tasks if t.completed == completed]

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_conflicts(scheduled_tasks: list[ScheduledTask]) -> list[str]:
        """Check all scheduled task pairs for time overlap; return a list of warning strings.

        Overlap condition: task A and task B conflict if A starts before B ends
        AND B starts before A ends.  This is the standard interval-overlap formula.
        Returns warnings rather than raising exceptions so the plan can still be used.
        """
        fmt      = "%H:%M"
        warnings = []

        for i, a in enumerate(scheduled_tasks):
            a_start = datetime.strptime(a.start_time, fmt)
            a_end   = datetime.strptime(a.end_time,   fmt)
            for b in scheduled_tasks[i + 1:]:
                b_start = datetime.strptime(b.start_time, fmt)
                b_end   = datetime.strptime(b.end_time,   fmt)
                if a_start < b_end and b_start < a_end:
                    warnings.append(
                        f"'{a.task.title}' ({a.start_time}-{a.end_time}) "
                        f"overlaps '{b.task.title}' ({b.start_time}-{b.end_time})"
                    )
        return warnings

    # ------------------------------------------------------------------
    # Private time helpers
    # ------------------------------------------------------------------

    def _fits_budget(self, task: CareTask, remaining: int) -> bool:
        """Return True if the task duration fits within the remaining time budget."""
        return task.is_schedulable(remaining)

    def _assign_time(self, task: CareTask, current_time: str) -> tuple[str, str]:
        """Calculate start and end time strings for a task given the current cursor."""
        start_dt = datetime.strptime(current_time, self._TIME_FMT)
        end_dt   = start_dt + timedelta(minutes=task.duration_minutes)
        return start_dt.strftime(self._TIME_FMT), end_dt.strftime(self._TIME_FMT)

    def _generate_reason(self, task: CareTask) -> str:
        """Build a human-readable explanation for why this task was scheduled."""
        parts = [f"{task.priority.name} priority"]
        if task.is_mandatory:
            parts.append("mandatory")
        if task.preferred_time:
            parts.append(f"preferred time {task.preferred_time}")
        if task.frequency != "once":
            parts.append(f"recurs {task.frequency}")
        return "Scheduled - " + ", ".join(parts)