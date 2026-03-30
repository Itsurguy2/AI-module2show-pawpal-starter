# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

The initial UML for PawPal+ was designed around a clean separation between data, output, and logic. Eight classes were defined:

- **`Priority` (Enum)** — Assigns a numeric weight (HIGH=3, MEDIUM=2, LOW=1) to tasks so the scheduler can rank them consistently.
- **`TaskCategory` (Enum)** — Labels each task with its type (WALK, FEEDING, MEDICATION, ENRICHMENT, GROOMING, VET_VISIT, PLAY) for grouping and display in the UI.
- **`CareTask`** — The core unit of the system. Holds everything needed to describe one care activity: its title, category, duration, priority, whether it is mandatory, a preferred start time, and how often it recurs. Responsible for knowing whether it can fit in a given time budget via `is_schedulable()`.
- **`Pet`** — Represents the animal being cared for. Stores identity and medical context, and owns the list of `CareTask` objects assigned to it.
- **`Owner`** — Represents the human user. Stores the total time budget for the day, the wake time that anchors the schedule, and any preferred task ordering. Owns the list of pets.
- **`ScheduledTask`** — A value object (no logic) that pairs a `CareTask` with its assigned start time, end time, and the reason it was chosen. Created by the Scheduler during planning.
- **`DailyPlan`** — The final output of the system. Holds the full list of scheduled and skipped tasks, tracks total minutes used, and exposes `get_summary()` and `get_explanation()` for the UI to display.
- **`Scheduler`** — The brain of the system. Takes an `Owner` and a `Pet`, sorts tasks by priority and mandatory status, fits them into the owner's time budget, assigns time slots, and produces a `DailyPlan`.

**b. Design changes**

Two changes were made after reviewing the skeleton against the UML:

**Change 1 — Added `SkippedTask` dataclass**

The original design stored skipped tasks as `list[CareTask]` inside `DailyPlan`. This was a logic bottleneck: `DailyPlan.get_explanation()` needs to explain *why* each task was dropped (e.g. "not enough time remaining" vs "lower priority than mandatory tasks"), but a plain `CareTask` carries no reason field. A new `SkippedTask` dataclass was added — mirroring the structure of `ScheduledTask` — with a `task` field and a `reason` field. `DailyPlan.skipped_tasks` was updated from `list[CareTask]` to `list[SkippedTask]`.

**Change 2 — Added `init=False` to private list fields in `Pet` and `Owner`**

The `_tasks` field on `Pet` and the `_pets` field on `Owner` were defined as dataclass fields without `init=False`. In Python dataclasses, any field without `init=False` becomes a constructor parameter — meaning callers would be expected to pass `_tasks=[...]` when creating a `Pet`, which is unintended. Adding `init=False` removes them from the generated `__init__`, so `Pet` and `Owner` are created with no tasks/pets and they are added via `add_task()` and `add_pet()` as intended.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers four constraints, applied in this order of importance:

1. **Mandatory flag** — Tasks marked `is_mandatory=True` are always sorted to the top of the queue. A missed medication or feeding has direct health consequences, so these tasks must be attempted before any optional activity regardless of priority level.

2. **Priority level** — After mandatory tasks, the scheduler ranks by `Priority` enum value (HIGH=3, MEDIUM=2, LOW=1). This reflects the real-world reality that a walk matters more than grooming on a busy day.

3. **Time budget** — The `Owner.available_minutes` acts as a hard ceiling. If a task's `duration_minutes` exceeds the remaining budget it is skipped and moved to `skipped_tasks` with a reason. The budget constraint was ranked above preferred time because an overbooked schedule is worse than a slightly mis-timed one.

4. **Preferred time** — Tasks with a `preferred_time` are sorted ahead of those without, but the scheduler does not guarantee a task starts at its preferred time. It uses `preferred_time` as a tiebreaker in sorting, not as a strict reservation.

The decision to prioritize mandatory > priority level > budget > preferred time came from thinking about what causes the most harm if violated: missing medication is worse than a walk starting at 8:05 instead of 8:00.

**b. Tradeoffs**

**Tradeoff: Sequential scheduling vs. preferred-time honoring**

The scheduler assigns tasks one after another starting from `owner.wake_time`. Each task's start time is the end time of the previous task — there are no gaps or jumps to honor `preferred_time` slots.

This means a task set for "09:00" may actually run at "07:15" if higher-priority tasks are short. The benefit of this approach is simplicity and zero conflicts: sequential scheduling mathematically cannot produce overlapping tasks. The cost is that the schedule may feel off to an owner who specifically wanted the walk at 9am.

The alternative — placing each task at its `preferred_time` and filling gaps — would require gap-filling logic, conflict resolution, and handling of orphaned time windows. For a daily pet care tool used by a single owner, the sequential approach is a reasonable tradeoff: the owner sees a clear, gapless plan they can follow top to bottom without checking a clock constantly. The conflict detection feature exists precisely to flag when preferred times *would* clash, even though the sequential planner avoids them automatically.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
