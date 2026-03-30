"""
tests/test_pawpal.py — Pytest tests for PawPal+ core logic.
Run with:  py -m pytest
"""

import pytest
from datetime import date, timedelta
from pawpal_system import (
    CareTask,
    DailyPlan,
    Owner,
    ScheduledTask,
    Pet,
    Priority,
    Scheduler,
    TaskCategory,
)


# ---------------------------------------------------------------------------
# Fixtures — reusable test objects
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_task():
    """A basic high-priority walk task."""
    return CareTask(
        task_id="t1",
        title="Morning Walk",
        category=TaskCategory.WALK,
        duration_minutes=30,
        priority=Priority.HIGH,
    )


@pytest.fixture
def sample_pet():
    """A pet with no tasks attached."""
    return Pet(name="Mochi", species="dog", age=3)


@pytest.fixture
def sample_owner():
    """An owner with a 120-minute daily budget starting at 07:00."""
    return Owner(name="Jordan", available_minutes=120, wake_time="07:00")


# ---------------------------------------------------------------------------
# CareTask tests
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status(sample_task):
    """Calling mark_complete() should flip completed from False to True."""
    assert sample_task.completed is False
    sample_task.mark_complete()
    assert sample_task.completed is True


def test_mark_complete_is_idempotent(sample_task):
    """Calling mark_complete() twice should not raise and status stays True."""
    sample_task.mark_complete()
    sample_task.mark_complete()
    assert sample_task.completed is True


def test_is_schedulable_fits(sample_task):
    """Task that fits within the budget should return True."""
    assert sample_task.is_schedulable(30) is True
    assert sample_task.is_schedulable(60) is True


def test_is_schedulable_does_not_fit(sample_task):
    """Task that exceeds the budget should return False."""
    assert sample_task.is_schedulable(29) is False
    assert sample_task.is_schedulable(0)  is False


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

def test_add_task_increases_count(sample_pet, sample_task):
    """Adding a task to a pet should increase its task count by 1."""
    assert len(sample_pet.get_tasks()) == 0
    sample_pet.add_task(sample_task)
    assert len(sample_pet.get_tasks()) == 1


def test_add_multiple_tasks(sample_pet):
    """Adding three tasks should result in a count of three."""
    for i in range(3):
        task = CareTask(
            task_id=f"t{i}",
            title=f"Task {i}",
            category=TaskCategory.PLAY,
            duration_minutes=10,
            priority=Priority.LOW,
        )
        sample_pet.add_task(task)
    assert len(sample_pet.get_tasks()) == 3


def test_get_tasks_returns_copy(sample_pet, sample_task):
    """get_tasks() should return a copy so external mutation doesn't affect the pet."""
    sample_pet.add_task(sample_task)
    tasks = sample_pet.get_tasks()
    tasks.clear()
    assert len(sample_pet.get_tasks()) == 1


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

def test_add_pet_increases_count(sample_owner, sample_pet):
    """Adding a pet to an owner should increase the pet count by 1."""
    assert len(sample_owner.get_pets()) == 0
    sample_owner.add_pet(sample_pet)
    assert len(sample_owner.get_pets()) == 1


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

def test_scheduler_schedules_fitting_tasks(sample_owner, sample_pet):
    """Tasks that fit within the budget should appear in scheduled_tasks."""
    task = CareTask(
        task_id="t1",
        title="Morning Walk",
        category=TaskCategory.WALK,
        duration_minutes=30,
        priority=Priority.HIGH,
    )
    sample_pet.add_task(task)
    sample_owner.add_pet(sample_pet)

    scheduler = Scheduler(owner=sample_owner, pet=sample_pet)
    plan = scheduler.build_plan("2026-03-29")

    assert len(plan.scheduled_tasks) == 1
    assert plan.scheduled_tasks[0].task.title == "Morning Walk"


def test_scheduler_skips_tasks_that_dont_fit(sample_owner):
    """A task longer than the available budget should be skipped."""
    owner = Owner(name="Jordan", available_minutes=10, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask(
        task_id="t1",
        title="Long Grooming",
        category=TaskCategory.GROOMING,
        duration_minutes=60,
        priority=Priority.LOW,
    ))
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner, pet=pet)
    plan = scheduler.build_plan("2026-03-29")

    assert len(plan.scheduled_tasks) == 0
    assert len(plan.skipped_tasks)   == 1


def test_mandatory_tasks_scheduled_first():
    """Mandatory tasks should appear before non-mandatory tasks of equal priority."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    pet   = Pet(name="Luna", species="cat", age=4)

    pet.add_task(CareTask(
        task_id="t1",
        title="Play Session",
        category=TaskCategory.PLAY,
        duration_minutes=15,
        priority=Priority.HIGH,
        is_mandatory=False,
    ))
    pet.add_task(CareTask(
        task_id="t2",
        title="Medication",
        category=TaskCategory.MEDICATION,
        duration_minutes=5,
        priority=Priority.HIGH,
        is_mandatory=True,
    ))
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner, pet=pet)
    plan = scheduler.build_plan("2026-03-29")

    assert plan.scheduled_tasks[0].task.title == "Medication"


def test_total_minutes_used_is_accurate():
    """total_minutes_used should equal the sum of all scheduled task durations."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)

    durations = [10, 20, 15]
    for i, d in enumerate(durations):
        pet.add_task(CareTask(
            task_id=f"t{i}",
            title=f"Task {i}",
            category=TaskCategory.WALK,
            duration_minutes=d,
            priority=Priority.MEDIUM,
        ))
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner, pet=pet)
    plan = scheduler.build_plan("2026-03-29")

    assert plan.total_minutes_used == sum(durations)


def test_plan_summary_contains_key_info():
    """get_summary() should mention task counts and minutes used."""
    owner = Owner(name="Jordan", available_minutes=60, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask(
        task_id="t1",
        title="Walk",
        category=TaskCategory.WALK,
        duration_minutes=30,
        priority=Priority.HIGH,
    ))
    owner.add_pet(pet)

    plan = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")
    summary = plan.get_summary()

    assert "1 task(s) scheduled" in summary
    assert "30 min used" in summary


# ---------------------------------------------------------------------------
# sort_by_time tests
# ---------------------------------------------------------------------------

def test_sort_by_time_orders_correctly():
    """Tasks should be sorted by preferred_time string ascending."""
    tasks = [
        CareTask("t1", "Walk",     TaskCategory.WALK,     30, Priority.HIGH,   preferred_time="09:00"),
        CareTask("t2", "Meds",     TaskCategory.MEDICATION, 5, Priority.HIGH,  preferred_time="07:00"),
        CareTask("t3", "Grooming", TaskCategory.GROOMING,  20, Priority.LOW,   preferred_time="08:00"),
    ]
    result = Scheduler.sort_by_time(tasks)
    assert [t.preferred_time for t in result] == ["07:00", "08:00", "09:00"]


def test_sort_by_time_pushes_no_preference_to_end():
    """Tasks without preferred_time should sort after tasks that have one."""
    tasks = [
        CareTask("t1", "Grooming", TaskCategory.GROOMING, 20, Priority.LOW),
        CareTask("t2", "Meds",     TaskCategory.MEDICATION, 5, Priority.HIGH, preferred_time="07:00"),
    ]
    result = Scheduler.sort_by_time(tasks)
    assert result[0].title == "Meds"
    assert result[1].title == "Grooming"


# ---------------------------------------------------------------------------
# filter_by_status tests
# ---------------------------------------------------------------------------

def test_filter_by_status_pending():
    """filter_by_status(completed=False) should return only incomplete tasks."""
    t1 = CareTask("t1", "Walk", TaskCategory.WALK, 30, Priority.HIGH)
    t2 = CareTask("t2", "Feed", TaskCategory.FEEDING, 10, Priority.HIGH)
    t2.mark_complete()

    result = Scheduler.filter_by_status([t1, t2], completed=False)
    assert len(result) == 1
    assert result[0].title == "Walk"


def test_filter_by_status_completed():
    """filter_by_status(completed=True) should return only completed tasks."""
    t1 = CareTask("t1", "Walk", TaskCategory.WALK, 30, Priority.HIGH)
    t2 = CareTask("t2", "Feed", TaskCategory.FEEDING, 10, Priority.HIGH)
    t2.mark_complete()

    result = Scheduler.filter_by_status([t1, t2], completed=True)
    assert len(result) == 1
    assert result[0].title == "Feed"


def test_filter_by_status_empty_list():
    """Filtering an empty list should return an empty list."""
    assert Scheduler.filter_by_status([], completed=False) == []


# ---------------------------------------------------------------------------
# next_occurrence tests
# ---------------------------------------------------------------------------

def test_next_occurrence_daily():
    """Daily task next_occurrence should have due_date = from_date + 1 day."""
    task = CareTask("t1", "Feed", TaskCategory.FEEDING, 10, Priority.HIGH, frequency="daily")
    next_task = task.next_occurrence("2026-03-29")
    assert next_task.due_date == "2026-03-30"
    assert next_task.completed is False


def test_next_occurrence_weekly():
    """Weekly task next_occurrence should have due_date = from_date + 7 days."""
    task = CareTask("t1", "Grooming", TaskCategory.GROOMING, 30, Priority.LOW, frequency="weekly")
    next_task = task.next_occurrence("2026-03-29")
    assert next_task.due_date == "2026-04-05"


def test_next_occurrence_resets_completed():
    """The returned next occurrence should always have completed=False."""
    task = CareTask("t1", "Walk", TaskCategory.WALK, 30, Priority.HIGH, frequency="daily")
    task.mark_complete()
    next_task = task.next_occurrence("2026-03-29")
    assert next_task.completed is False


def test_next_occurrence_once_returns_none():
    """A task with frequency='once' should return None for next_occurrence."""
    task = CareTask("t1", "Vet", TaskCategory.VET_VISIT, 60, Priority.HIGH, frequency="once")
    assert task.next_occurrence("2026-03-29") is None


def test_next_occurrence_new_task_id():
    """next_occurrence should produce a new task_id so it doesn't replace the original."""
    task = CareTask("m1", "Meds", TaskCategory.MEDICATION, 5, Priority.HIGH, frequency="daily")
    next_task = task.next_occurrence("2026-03-29")
    assert next_task.task_id != task.task_id


# ---------------------------------------------------------------------------
# conflict detection tests
# ---------------------------------------------------------------------------

def test_detect_conflicts_finds_overlap():
    """Two tasks with overlapping windows should produce one conflict warning."""
    task_a = CareTask("t1", "Walk",  TaskCategory.WALK,    30, Priority.HIGH)
    task_b = CareTask("t2", "Feed",  TaskCategory.FEEDING, 10, Priority.HIGH)

    scheduled = [
        ScheduledTask(task=task_a, start_time="07:00", end_time="07:30", reason=""),
        ScheduledTask(task=task_b, start_time="07:20", end_time="07:30", reason=""),
    ]
    warnings = Scheduler.detect_conflicts(scheduled)
    assert len(warnings) == 1
    assert "Walk" in warnings[0]
    assert "Feed" in warnings[0]


def test_detect_conflicts_no_overlap():
    """Tasks that are back-to-back but not overlapping should produce no warnings."""
    task_a = CareTask("t1", "Walk", TaskCategory.WALK,    30, Priority.HIGH)
    task_b = CareTask("t2", "Feed", TaskCategory.FEEDING, 10, Priority.HIGH)

    scheduled = [
        ScheduledTask(task=task_a, start_time="07:00", end_time="07:30", reason=""),
        ScheduledTask(task=task_b, start_time="07:30", end_time="07:40", reason=""),
    ]
    assert Scheduler.detect_conflicts(scheduled) == []


def test_detect_conflicts_stored_in_plan():
    """build_plan() should run conflict detection and conflicts should be empty for normal plans."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask("t1", "Walk", TaskCategory.WALK, 30, Priority.HIGH))
    owner.add_pet(pet)

    plan = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")
    # Sequential scheduling cannot produce conflicts
    assert plan.conflicts == []


# ---------------------------------------------------------------------------
# filter_tasks_by_pet tests
# ---------------------------------------------------------------------------

def test_filter_tasks_by_pet_correct_pet():
    """filter_tasks_by_pet should return tasks for the named pet only."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    mochi = Pet(name="Mochi", species="dog", age=3)
    luna  = Pet(name="Luna",  species="cat", age=5)
    mochi.add_task(CareTask("t1", "Walk", TaskCategory.WALK,    30, Priority.HIGH))
    luna.add_task( CareTask("t2", "Feed", TaskCategory.FEEDING, 10, Priority.HIGH))
    owner.add_pet(mochi)
    owner.add_pet(luna)

    result = owner.filter_tasks_by_pet("Mochi")
    assert len(result) == 1
    assert result[0].title == "Walk"


def test_filter_tasks_by_pet_case_insensitive():
    """filter_tasks_by_pet should work regardless of letter case."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask("t1", "Walk", TaskCategory.WALK, 30, Priority.HIGH))
    owner.add_pet(pet)

    assert len(owner.filter_tasks_by_pet("mochi")) == 1
    assert len(owner.filter_tasks_by_pet("MOCHI")) == 1


def test_filter_tasks_by_pet_unknown_name():
    """filter_tasks_by_pet with an unknown name should return an empty list."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    owner.add_pet(Pet(name="Mochi", species="dog", age=3))
    assert owner.filter_tasks_by_pet("Rex") == []


# ===========================================================================
# EDGE CASES — things that can go wrong or are easy to overlook
# ===========================================================================

# ---------------------------------------------------------------------------
# Edge case: pet with no tasks
# ---------------------------------------------------------------------------

def test_pet_with_no_tasks_returns_empty_plan():
    """Happy path: a pet that has no tasks should produce a plan with nothing scheduled."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    owner.add_pet(pet)  # pet has zero tasks

    plan = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")

    assert len(plan.scheduled_tasks)  == 0
    assert len(plan.skipped_tasks)    == 0
    assert plan.total_minutes_used    == 0
    assert plan.conflicts             == []


# ---------------------------------------------------------------------------
# Edge case: all tasks already completed
# ---------------------------------------------------------------------------

def test_completed_tasks_are_excluded_from_schedule():
    """Edge case: tasks already marked complete should not appear in the plan.

    build_plan() filters out completed tasks before scheduling, so an owner
    who finishes everything early should see an empty plan on re-run.
    """
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)

    task = CareTask("t1", "Walk", TaskCategory.WALK, 30, Priority.HIGH)
    task.mark_complete()
    pet.add_task(task)
    owner.add_pet(pet)

    plan = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")

    assert len(plan.scheduled_tasks) == 0


# ---------------------------------------------------------------------------
# Edge case: zero time budget
# ---------------------------------------------------------------------------

def test_zero_budget_skips_all_tasks():
    """Edge case: an owner with 0 available minutes should have every task skipped."""
    owner = Owner(name="Jordan", available_minutes=0, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask("t1", "Walk", TaskCategory.WALK, 30, Priority.HIGH))
    pet.add_task(CareTask("t2", "Feed", TaskCategory.FEEDING, 10, Priority.HIGH))
    owner.add_pet(pet)

    plan = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")

    assert len(plan.scheduled_tasks) == 0
    assert len(plan.skipped_tasks)   == 2


def test_task_exactly_fills_budget_is_scheduled():
    """Edge case: a task whose duration exactly equals the budget should be scheduled."""
    owner = Owner(name="Jordan", available_minutes=30, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask("t1", "Walk", TaskCategory.WALK, 30, Priority.HIGH))
    owner.add_pet(pet)

    plan = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")

    assert len(plan.scheduled_tasks) == 1
    assert plan.total_minutes_used   == 30


# ---------------------------------------------------------------------------
# Edge case: time assignment correctness
# ---------------------------------------------------------------------------

def test_first_task_starts_at_wake_time():
    """Happy path: the first scheduled task should start exactly at the owner's wake time."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="08:30")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask("t1", "Walk", TaskCategory.WALK, 30, Priority.HIGH))
    owner.add_pet(pet)

    plan = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")

    assert plan.scheduled_tasks[0].start_time == "08:30"


def test_tasks_are_assigned_sequentially():
    """Happy path: the second task's start time should equal the first task's end time."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask("t1", "Walk", TaskCategory.WALK,    30, Priority.HIGH))
    pet.add_task(CareTask("t2", "Feed", TaskCategory.FEEDING, 10, Priority.MEDIUM))
    owner.add_pet(pet)

    plan = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")

    first  = plan.scheduled_tasks[0]
    second = plan.scheduled_tasks[1]
    assert second.start_time == first.end_time


def test_task_end_time_equals_start_plus_duration():
    """Happy path: end_time should be exactly start_time + duration_minutes."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask("t1", "Walk", TaskCategory.WALK, 45, Priority.HIGH))
    owner.add_pet(pet)

    plan  = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")
    entry = plan.scheduled_tasks[0]

    assert entry.start_time == "07:00"
    assert entry.end_time   == "07:45"


# ---------------------------------------------------------------------------
# Edge case: sorting with all tasks at the same time
# ---------------------------------------------------------------------------

def test_sort_by_time_empty_list():
    """Edge case: sorting an empty task list should return an empty list."""
    assert Scheduler.sort_by_time([]) == []


def test_sort_by_time_all_same_preferred_time():
    """Edge case: tasks sharing the same preferred_time should all be returned (stable order)."""
    tasks = [
        CareTask("t1", "Walk", TaskCategory.WALK,    30, Priority.HIGH,   preferred_time="07:00"),
        CareTask("t2", "Feed", TaskCategory.FEEDING, 10, Priority.MEDIUM, preferred_time="07:00"),
    ]
    result = Scheduler.sort_by_time(tasks)
    # Both should be present; order among ties is stable
    assert len(result) == 2
    assert all(t.preferred_time == "07:00" for t in result)


# ---------------------------------------------------------------------------
# Edge case: conflict detection — exact same start time
# ---------------------------------------------------------------------------

def test_detect_conflicts_exact_same_start_time():
    """Edge case: two tasks starting at exactly the same time are always a conflict."""
    task_a = CareTask("t1", "Walk", TaskCategory.WALK,    30, Priority.HIGH)
    task_b = CareTask("t2", "Feed", TaskCategory.FEEDING, 10, Priority.HIGH)

    scheduled = [
        ScheduledTask(task=task_a, start_time="07:00", end_time="07:30", reason=""),
        ScheduledTask(task=task_b, start_time="07:00", end_time="07:10", reason=""),
    ]
    warnings = Scheduler.detect_conflicts(scheduled)
    assert len(warnings) == 1


def test_detect_conflicts_empty_scheduled_list():
    """Edge case: an empty scheduled list should produce no conflict warnings."""
    assert Scheduler.detect_conflicts([]) == []


def test_detect_conflicts_only_conflicting_pair_flagged():
    """Edge case: only the overlapping pair should appear in warnings, not safe pairs."""
    task_a = CareTask("t1", "Walk",     TaskCategory.WALK,      30, Priority.HIGH)
    task_b = CareTask("t2", "Feed",     TaskCategory.FEEDING,   10, Priority.HIGH)
    task_c = CareTask("t3", "Grooming", TaskCategory.GROOMING,  20, Priority.LOW)

    scheduled = [
        ScheduledTask(task=task_a, start_time="07:00", end_time="07:30", reason=""),
        ScheduledTask(task=task_b, start_time="07:20", end_time="07:30", reason=""),  # overlaps a
        ScheduledTask(task=task_c, start_time="07:30", end_time="07:50", reason=""),  # safe
    ]
    warnings = Scheduler.detect_conflicts(scheduled)
    assert len(warnings) == 1  # only a vs b, not a vs c or b vs c


# ---------------------------------------------------------------------------
# Edge case: next_occurrence preserves original properties
# ---------------------------------------------------------------------------

def test_next_occurrence_preserves_task_properties():
    """Edge case: next_occurrence should keep title, category, duration, and priority intact."""
    original = CareTask(
        task_id="t1", title="Morning Meds",
        category=TaskCategory.MEDICATION, duration_minutes=5,
        priority=Priority.HIGH, is_mandatory=True, frequency="daily",
    )
    original.mark_complete()
    next_task = original.next_occurrence("2026-03-29")

    assert next_task.title            == original.title
    assert next_task.category         == original.category
    assert next_task.duration_minutes == original.duration_minutes
    assert next_task.priority         == original.priority
    assert next_task.is_mandatory     == original.is_mandatory


# ---------------------------------------------------------------------------
# Edge case: get_explanation surfaces conflict warnings
# ---------------------------------------------------------------------------

def test_get_explanation_includes_conflict_warnings():
    """Edge case: if DailyPlan has conflicts, get_explanation() should mention them."""
    owner = Owner(name="Jordan", available_minutes=120, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask("t1", "Walk", TaskCategory.WALK, 30, Priority.HIGH))
    owner.add_pet(pet)

    plan = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")
    # Inject a fake conflict warning to verify get_explanation() surfaces it
    plan.conflicts.append("'Walk' (07:00-07:30) overlaps 'Feed' (07:15-07:25)")

    explanation = plan.get_explanation()
    assert "CONFLICT WARNINGS" in explanation
    assert "Walk" in explanation


# ---------------------------------------------------------------------------
# Edge case: skipped task reason is informative
# ---------------------------------------------------------------------------

def test_skipped_task_reason_mentions_duration():
    """Edge case: when a task is skipped, its reason should mention the time needed."""
    owner = Owner(name="Jordan", available_minutes=10, wake_time="07:00")
    pet   = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(CareTask("t1", "Grooming", TaskCategory.GROOMING, 60, Priority.LOW))
    owner.add_pet(pet)

    plan = Scheduler(owner=owner, pet=pet).build_plan("2026-03-29")

    assert len(plan.skipped_tasks) == 1
    reason = plan.skipped_tasks[0].reason
    assert "60" in reason   # mentions how many minutes were needed
    assert "10" in reason   # mentions how many minutes were available