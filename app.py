"""
app.py — PawPal+ Streamlit UI
Connected to the backend logic in pawpal_system.py.
Run with:  py -m streamlit run app.py
"""

import streamlit as st
from datetime import date

from pawpal_system import (
    CareTask,
    Owner,
    Pet,
    Priority,
    Scheduler,
    TaskCategory,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="PawPal+", page_icon="PawPal+", layout="centered")
st.title("PawPal+")
st.caption("Your smart pet care daily planner")

# ---------------------------------------------------------------------------
# Session state — the app's persistent memory across re-runs
# ---------------------------------------------------------------------------
if "owner"        not in st.session_state: st.session_state.owner        = None
if "pet"          not in st.session_state: st.session_state.pet          = None
if "task_counter" not in st.session_state: st.session_state.task_counter = 0
if "last_plan"    not in st.session_state: st.session_state.last_plan    = None
if "plan_date"    not in st.session_state: st.session_state.plan_date    = date.today()

# ---------------------------------------------------------------------------
# Helper maps
# ---------------------------------------------------------------------------
PRIORITY_MAP = {"High": Priority.HIGH, "Medium": Priority.MEDIUM, "Low": Priority.LOW}
CATEGORY_MAP = {
    "Walk":       TaskCategory.WALK,
    "Feeding":    TaskCategory.FEEDING,
    "Medication": TaskCategory.MEDICATION,
    "Enrichment": TaskCategory.ENRICHMENT,
    "Grooming":   TaskCategory.GROOMING,
    "Vet Visit":  TaskCategory.VET_VISIT,
    "Play":       TaskCategory.PLAY,
}
FREQ_OPTIONS = ["daily", "weekly", "once"]

# ===========================================================================
# SECTION 1 — Owner & Pet Profile
# ===========================================================================
st.divider()
st.subheader("Step 1 - Owner & Pet Profile")
st.caption("Create your profile first. You can update it at any time.")

with st.form("setup_form"):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Owner info**")
        owner_name = st.text_input("Your name", value="Jordan")
        budget     = st.number_input("Available minutes today", min_value=0, max_value=720, value=180,
                                     help="Total minutes available for pet care today.")
        wake_time  = st.text_input("Wake time (HH:MM)", value="07:00",
                                   help="Schedule starts here.")
    with col_b:
        st.markdown("**Pet info**")
        pet_name = st.text_input("Pet name", value="Mochi")
        species  = st.selectbox("Species", ["dog", "cat", "other"])
        age      = st.number_input("Age (years)", min_value=0, max_value=30, value=3)

    profile_submitted = st.form_submit_button("Create / Update Profile", type="primary")

if profile_submitted:
    new_owner = Owner(name=owner_name, available_minutes=int(budget), wake_time=wake_time)
    new_pet   = Pet(name=pet_name, species=species, age=int(age))
    new_owner.add_pet(new_pet)
    st.session_state.owner        = new_owner
    st.session_state.pet          = new_pet
    st.session_state.task_counter = 0
    st.session_state.last_plan    = None
    st.success(f"Profile saved!  Owner: {owner_name}  |  Pet: {pet_name} ({species})")

# ===========================================================================
# SECTION 2 — Add Care Tasks
# ===========================================================================
if st.session_state.pet is not None:
    st.divider()
    st.subheader("Step 2 - Add Care Tasks")
    st.caption(f"Adding tasks for **{st.session_state.pet.name}**.")

    with st.form("task_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            task_title   = st.text_input("Task title", value="Morning Walk")
            category_key = st.selectbox("Category", list(CATEGORY_MAP.keys()))
            frequency    = st.selectbox("Frequency", FREQ_OPTIONS)
        with col2:
            duration     = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
            priority_key = st.selectbox("Priority", list(PRIORITY_MAP.keys()))
        with col3:
            is_mandatory   = st.checkbox("Mandatory?",
                                         help="Mandatory tasks are always scheduled first.")
            preferred_time = st.text_input("Preferred time (HH:MM)", value="",
                                           placeholder="optional")

        task_submitted = st.form_submit_button("Add Task")

    if task_submitted:
        st.session_state.task_counter += 1
        new_task = CareTask(
            task_id          = f"t{st.session_state.task_counter}",
            title            = task_title,
            category         = CATEGORY_MAP[category_key],
            duration_minutes = int(duration),
            priority         = PRIORITY_MAP[priority_key],
            is_mandatory     = is_mandatory,
            preferred_time   = preferred_time.strip() or None,
            frequency        = frequency,
        )
        st.session_state.pet.add_task(new_task)
        st.success(f"Added: {task_title} ({duration} min, {priority_key}, {frequency})")

    # -----------------------------------------------------------------------
    # Task table — default view
    # -----------------------------------------------------------------------
    current_tasks = st.session_state.pet.get_tasks()
    if current_tasks:
        tab_all, tab_sorted, tab_pending, tab_done = st.tabs(
            ["All Tasks", "Sorted by Time", "Pending", "Completed"]
        )

        def _task_rows(tasks):
            return [
                {
                    "Title":          t.title,
                    "Category":       t.category.value,
                    "Duration (min)": t.duration_minutes,
                    "Priority":       t.priority.name,
                    "Mandatory":      "Yes" if t.is_mandatory else "No",
                    "Preferred Time": t.preferred_time or "—",
                    "Frequency":      t.frequency,
                    "Done":           "Yes" if t.completed else "No",
                }
                for t in tasks
            ]

        with tab_all:
            active = Scheduler.filter_by_status(current_tasks, completed=False)
            st.caption(f"{len(active)} active task(s) for {st.session_state.pet.name}")
            st.dataframe(_task_rows(active), use_container_width=True, hide_index=True)

        with tab_sorted:
            sorted_tasks = Scheduler.sort_by_time(current_tasks)
            st.caption("Tasks ordered by preferred time (earliest first). Tasks with no preference appear last.")
            st.dataframe(_task_rows(sorted_tasks), use_container_width=True, hide_index=True)

        with tab_pending:
            pending = Scheduler.filter_by_status(current_tasks, completed=False)
            if pending:
                st.caption(f"{len(pending)} task(s) still to do today.")
                st.dataframe(_task_rows(pending), use_container_width=True, hide_index=True)
            else:
                st.success("All tasks completed for today!")

        with tab_done:
            done = Scheduler.filter_by_status(current_tasks, completed=True)
            if done:
                st.caption(f"{len(done)} task(s) finished.")
                st.dataframe(_task_rows(done), use_container_width=True, hide_index=True)
            else:
                st.info("No completed tasks yet.")

        # -------------------------------------------------------------------
        # Mark task complete + recurring next occurrence
        # -------------------------------------------------------------------
        st.divider()
        st.markdown("**Mark a Task Complete**")
        pending_tasks = Scheduler.filter_by_status(current_tasks, completed=False)
        if pending_tasks:
            task_to_complete = st.selectbox(
                "Select task to mark done",
                options=pending_tasks,
                format_func=lambda t: t.title,
            )
            if st.button("Mark Complete"):
                task_to_complete.mark_complete()
                if task_to_complete.frequency != "once":
                    from_date = st.session_state.plan_date.strftime("%Y-%m-%d")
                    next_t    = task_to_complete.next_occurrence(from_date)
                    st.session_state.pet.add_task(next_t)
                    st.session_state.last_plan = None  # clear stale plan
                    st.rerun()
                else:
                    st.session_state.last_plan = None
                    st.rerun()
        else:
            st.info("No pending tasks to complete.")

    else:
        st.info("No tasks yet. Add one above.")

# ===========================================================================
# SECTION 3 — Generate Daily Schedule
# ===========================================================================
if st.session_state.pet is not None and st.session_state.pet.get_tasks():
    st.divider()
    st.subheader("Step 3 - Generate Daily Schedule")
    st.caption(
        f"Owner: **{st.session_state.owner.name}**  |  "
        f"Budget: **{st.session_state.owner.available_minutes} min**  |  "
        f"Start: **{st.session_state.owner.wake_time}**"
    )

    st.session_state.plan_date = st.date_input(
        "Schedule date",
        value=st.session_state.plan_date,
        help="Pick the date you want to generate a plan for.",
    )

    if st.button("Generate Schedule", type="primary", use_container_width=True):
        plan_date_str = st.session_state.plan_date.strftime("%Y-%m-%d")
        scheduler     = Scheduler(owner=st.session_state.owner, pet=st.session_state.pet)
        plan          = scheduler.build_plan(date=plan_date_str)
        st.session_state.last_plan = plan

    # Display the plan (persists across re-runs via session_state)
    plan = st.session_state.last_plan
    if plan is not None:

        # -- Conflict warnings displayed first and prominently ---------------
        if plan.conflicts:
            st.error(
                f"**{len(plan.conflicts)} scheduling conflict(s) detected.** "
                "Review your preferred times — some tasks overlap."
            )
            for c in plan.conflicts:
                st.error(f"Conflict: {c}")

        # -- Summary banner ---------------------------------------------------
        if plan.conflicts:
            st.warning(plan.get_summary())
        else:
            st.success(plan.get_summary())

        # -- Scheduled tasks --------------------------------------------------
        if plan.scheduled_tasks:
            st.markdown("#### Scheduled Tasks")
            for entry in plan.scheduled_tasks:
                badge = "MANDATORY  " if entry.task.is_mandatory else ""
                with st.container(border=True):
                    time_col, detail_col = st.columns([1, 3])
                    with time_col:
                        st.markdown(f"**{entry.start_time}**")
                        st.caption(f"to {entry.end_time}")
                    with detail_col:
                        st.markdown(f"**{badge}{entry.task.title}**")
                        st.caption(
                            f"{entry.task.duration_minutes} min  |  "
                            f"{entry.task.priority.name} priority  |  "
                            f"recurs {entry.task.frequency}  |  "
                            f"{entry.reason}"
                        )

        # -- Skipped tasks ----------------------------------------------------
        if plan.skipped_tasks:
            st.markdown("#### Skipped Tasks")
            for skipped in plan.skipped_tasks:
                st.warning(
                    f"**{skipped.task.title}** ({skipped.task.duration_minutes} min) "
                    f"— {skipped.reason}"
                )
            st.caption(
                "Tip: reduce task durations, increase your time budget, "
                "or remove lower-priority tasks to fit more into your day."
            )