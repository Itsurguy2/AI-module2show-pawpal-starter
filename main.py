"""
main.py — CLI demo for PawPal+
Run with:  py main.py
"""

from datetime import date
from pawpal_system import (
    CareTask,
    Owner,
    Pet,
    Priority,
    Scheduler,
    ScheduledTask,
    TaskCategory,
)

DIVIDER = "-" * 55


def section(title: str) -> None:
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print(f"{'=' * 55}")


def main() -> None:
    today = date.today().strftime("%Y-%m-%d")

    # ------------------------------------------------------------------ #
    # Setup — owner and two pets                                           #
    # ------------------------------------------------------------------ #
    owner = Owner(name="Jordan", available_minutes=180, wake_time="07:00")

    mochi = Pet(name="Mochi", species="dog", age=3, breed="Shiba Inu")
    luna  = Pet(name="Luna",  species="cat", age=5, breed="Domestic Shorthair")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Tasks added OUT OF ORDER intentionally to demonstrate sorting
    mochi.add_task(CareTask(
        task_id="m1", title="Full Grooming Session",
        category=TaskCategory.GROOMING, duration_minutes=45,
        priority=Priority.LOW, preferred_time="10:00",
    ))
    mochi.add_task(CareTask(
        task_id="m2", title="Morning Medication",
        category=TaskCategory.MEDICATION, duration_minutes=5,
        priority=Priority.HIGH, is_mandatory=True,
        preferred_time="07:00", frequency="daily",
    ))
    mochi.add_task(CareTask(
        task_id="m3", title="Breakfast Feeding",
        category=TaskCategory.FEEDING, duration_minutes=10,
        priority=Priority.HIGH, is_mandatory=True,
        preferred_time="07:30", frequency="daily",
    ))
    mochi.add_task(CareTask(
        task_id="m4", title="Morning Walk",
        category=TaskCategory.WALK, duration_minutes=30,
        priority=Priority.HIGH, preferred_time="08:00",
        frequency="daily",
    ))
    mochi.add_task(CareTask(
        task_id="m5", title="Puzzle Toy Enrichment",
        category=TaskCategory.ENRICHMENT, duration_minutes=20,
        priority=Priority.MEDIUM, preferred_time="09:00",
        frequency="weekly",
    ))

    luna.add_task(CareTask(
        task_id="l1", title="Breakfast Feeding",
        category=TaskCategory.FEEDING, duration_minutes=10,
        priority=Priority.HIGH, is_mandatory=True,
        preferred_time="07:00", frequency="daily",
    ))
    luna.add_task(CareTask(
        task_id="l2", title="Playtime with Wand",
        category=TaskCategory.PLAY, duration_minutes=15,
        priority=Priority.MEDIUM, preferred_time="08:00",
        frequency="weekly",
    ))
    luna.add_task(CareTask(
        task_id="l3", title="Brush Coat",
        category=TaskCategory.GROOMING, duration_minutes=10,
        priority=Priority.LOW,
    ))

    # ------------------------------------------------------------------ #
    # 1. SORT BY TIME — shows lambda key on preferred_time strings         #
    # ------------------------------------------------------------------ #
    section("DEMO 1: Sort Tasks by Preferred Time")
    mochi_tasks = mochi.get_tasks()
    sorted_tasks = Scheduler.sort_by_time(mochi_tasks)

    print(f"\n  Mochi's tasks sorted by preferred_time (HH:MM):\n")
    for t in sorted_tasks:
        time_label = t.preferred_time if t.preferred_time else "no preference"
        print(f"  {time_label:12}  {t.title}")

    # ------------------------------------------------------------------ #
    # 2. FILTER BY STATUS — pending vs completed                           #
    # ------------------------------------------------------------------ #
    section("DEMO 2: Filter Tasks by Completion Status")

    # Mark one task complete first
    mochi_tasks[0].mark_complete()

    all_tasks = mochi.get_tasks()
    pending   = Scheduler.filter_by_status(all_tasks, completed=False)
    done      = Scheduler.filter_by_status(all_tasks, completed=True)

    print(f"\n  Pending ({len(pending)}):  ", [t.title for t in pending])
    print(f"  Completed ({len(done)}):  ", [t.title for t in done])

    # ------------------------------------------------------------------ #
    # 3. FILTER BY PET NAME                                                #
    # ------------------------------------------------------------------ #
    section("DEMO 3: Filter Tasks by Pet Name")
    luna_tasks = owner.filter_tasks_by_pet("Luna")
    print(f"\n  Tasks for Luna ({len(luna_tasks)}):")
    for t in luna_tasks:
        print(f"    - {t.title} ({t.category.value}, {t.duration_minutes} min)")

    # ------------------------------------------------------------------ #
    # 4. RECURRING TASKS — next_occurrence() with timedelta                #
    # ------------------------------------------------------------------ #
    section("DEMO 4: Recurring Tasks — next_occurrence()")

    daily_task  = mochi.get_tasks()[1]   # Morning Medication (daily)
    weekly_task = mochi.get_tasks()[4]   # Puzzle Toy Enrichment (weekly)

    daily_task.mark_complete()
    next_daily  = daily_task.next_occurrence(from_date=today)
    next_weekly = weekly_task.next_occurrence(from_date=today)

    print(f"\n  '{daily_task.title}' marked complete.")
    print(f"  Next daily occurrence  -> task_id: {next_daily.task_id}  due: {next_daily.due_date}")

    print(f"\n  '{weekly_task.title}' frequency = weekly")
    print(f"  Next weekly occurrence -> task_id: {next_weekly.task_id}  due: {next_weekly.due_date}")

    # ------------------------------------------------------------------ #
    # 5. CONFLICT DETECTION — two tasks with overlapping time windows      #
    # ------------------------------------------------------------------ #
    section("DEMO 5: Conflict Detection")

    # Manually construct two ScheduledTask objects with overlapping times
    # to demonstrate the overlap detection algorithm
    task_a = mochi.get_tasks()[2]   # Breakfast Feeding  07:30-07:40
    task_b = mochi.get_tasks()[3]   # Morning Walk       07:35-08:05  <-- overlaps!

    conflicting = [
        ScheduledTask(task=task_a, start_time="07:30", end_time="07:40", reason="demo"),
        ScheduledTask(task=task_b, start_time="07:35", end_time="08:05", reason="demo"),
    ]

    warnings = Scheduler.detect_conflicts(conflicting)
    if warnings:
        print(f"\n  {len(warnings)} conflict(s) found:")
        for w in warnings:
            print(f"    !! {w}")
    else:
        print("\n  No conflicts detected.")

    # ------------------------------------------------------------------ #
    # 6. FULL DAILY PLAN — scheduler runs all features together            #
    # ------------------------------------------------------------------ #
    section("DEMO 6: Full Daily Schedule")
    print()

    for pet in owner.get_pets():
        scheduler = Scheduler(owner=owner, pet=pet)
        plan = scheduler.build_plan(date=today)
        print(plan.get_explanation())
        if plan.conflicts:
            print("\n  CONFLICTS DETECTED IN PLAN:")
            for c in plan.conflicts:
                print(f"    !! {c}")
        print()


if __name__ == "__main__":
    main()