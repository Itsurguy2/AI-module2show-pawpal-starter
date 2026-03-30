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

AI was used as a collaborative engineering partner across every phase of this project, with a different role in each phase:

- **Phase 1 — Design brainstorming:** AI helped identify the right set of classes from the scenario description, suggested the `SkippedTask` wrapper (which the initial UML missed), and caught the `init=False` dataclass issue before any code was written. The most effective prompt style was describing a *goal* ("I need the plan to explain why tasks were skipped") rather than asking for a code snippet directly.

- **Phase 2 — Implementation:** AI generated method stubs and filled in logic for `_assign_time`, `_sort_tasks`, and `build_plan`. The most useful prompts were specific: "How should the Scheduler retrieve all tasks from the Owner's pets?" produced a clean `get_all_tasks()` pattern rather than a vague suggestion.

- **Phase 3 — Algorithms:** AI brainstormed the conflict detection algorithm and the `next_occurrence` pattern using `dataclasses.replace()`. Asking "what are edge cases to test for a pet scheduler with sorting and recurring tasks?" produced a test plan that surfaced cases (zero budget, all tasks completed, exact same start time) that would have been easy to overlook.

- **Phase 4 — Testing:** AI drafted test scaffolding quickly. The most valuable prompt pattern was asking AI to explain *why* a test was structured a certain way, which forced verification that the test was actually catching the right behavior.

**b. Judgment and verification**

During Phase 3, AI suggested using a dictionary (`{task: reason}`) to track skipped tasks instead of a `SkippedTask` dataclass. The suggestion was rejected for two reasons: a dictionary is harder to serialize, display in a table, and pass to typed functions, and it would have created an inconsistency — `ScheduledTask` is a dataclass, so `SkippedTask` should be one too for symmetry. The AI suggestion was evaluated by asking: "Does this fit the existing patterns in the codebase?" — it didn't, so the `SkippedTask` dataclass design was kept.

A second example: AI initially suggested using `datetime.time` objects internally instead of `"HH:MM"` strings. The string format was kept because Streamlit displays strings directly without conversion, and the `"%H:%M"` format is readable in the UI without extra formatting code.

---

## 4. Testing and Verification

**a. What you tested**

The test suite covers 44 behaviors across five areas:

1. **Core data classes** — `CareTask.mark_complete()`, `is_schedulable()`, `Pet.add_task()`, and `Owner.add_pet()` confirm that the building blocks of the system work in isolation before testing combinations.

2. **Scheduling logic** — Tests verify that mandatory tasks are always first, that tasks exceeding the budget are skipped with a reason, and that `total_minutes_used` exactly matches the sum of scheduled durations. These are critical because a scheduler that silently drops tasks or miscounts time would be unusable in practice.

3. **Smart algorithms** — `sort_by_time`, `filter_by_status`, `next_occurrence`, and `detect_conflicts` each have dedicated tests including both happy paths and edge cases. A test for `sort_by_time` on an already-sorted list verifies stability; a test for `detect_conflicts` with three tasks (only one pair overlapping) verifies the algorithm doesn't over-report.

4. **Edge cases** — Pet with no tasks, zero time budget, all tasks already completed, a task that exactly fills the budget, exact same start time conflicts, and `once`-frequency tasks returning `None` from `next_occurrence`. These catch off-by-one errors and boundary conditions that don't appear in normal use.

5. **Output quality** — `get_summary()` content test and `get_explanation()` conflict-surfacing test verify that the plan produces human-readable output — important because the UI depends entirely on these strings.

**b. Confidence**

**4.5 / 5.** The core scheduling logic, algorithm correctness, and edge case handling are thoroughly verified. The 0.5 gap reflects:
- The Streamlit UI layer is not covered by automated tests (requires browser interaction testing).
- Multi-pet conflict detection (tasks for different pets on the same owner's schedule) is not yet tested.
- Preferred-time honoring under tight budgets has only one test scenario — more coverage here would increase confidence.

If given more time, the next tests would be: a pet with 50+ tasks to verify performance doesn't degrade, tasks spanning midnight (e.g., "23:45" to "00:15"), and a full integration test driving the Streamlit app with `streamlit.testing`.

---

## 5. Reflection

**a. What went well**

The separation between the data layer (`CareTask`, `Pet`, `Owner`), the output layer (`ScheduledTask`, `SkippedTask`, `DailyPlan`), and the logic layer (`Scheduler`) worked exactly as designed. When new features were added in Phase 3 — sorting, filtering, conflict detection — they slotted in as static methods on `Scheduler` without touching any other class. The UML did its job: changes were additive, not structural. The `SkippedTask` design decision from Phase 1 also paid off in Phase 4 — the "skipped task reason mentions duration" edge case test would have been impossible to write if skipped tasks were stored as plain `CareTask` objects.

**b. What you would improve**

The scheduler currently ignores `preferred_time` when assigning actual start times — it uses `preferred_time` only as a sort key. A future iteration would implement a "preferred-time-first" mode: place each task at its preferred time if the slot is free, fall back to sequential only if the slot is taken. This would make the schedule feel more natural to the owner and would make the conflict detection feature genuinely necessary for normal use rather than just for edge case demos.

A second improvement would be multi-pet scheduling — a single `DailyPlan` covering all of the owner's pets, with shared time budget and cross-pet conflict detection.

**c. Key takeaway**

The most important lesson from this project is that **AI is a fast first-draft generator, not a design decision maker**. Every time the AI produced a suggestion — a method signature, a data structure, a test pattern — the useful question was not "does this code run?" but "does this fit the system I'm building?" The `dict` vs `SkippedTask` decision, the `datetime.time` vs string decision, and the choice to keep sequential scheduling over preferred-time placement were all moments where accepting the AI suggestion as-is would have made the code harder to read, test, or extend. The human role in an AI-assisted workflow is to hold the architectural vision and use AI to accelerate the *execution* of that vision — not to outsource the vision itself.
