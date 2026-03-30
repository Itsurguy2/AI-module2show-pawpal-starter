"""
app.py — PawPal+ Streamlit UI
Connected to the backend logic in pawpal_system.py.
Run with:  py -m streamlit run app.py
"""

import streamlit as st
from datetime import date

# ---------------------------------------------------------------------------
# Step 1: Import backend classes from the logic layer
# ---------------------------------------------------------------------------
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
# Step 2: Session state — the app's "memory"
#
# Streamlit re-runs the entire script on every interaction.
# st.session_state acts like a persistent dictionary across re-runs.
# We check if each key already exists before creating a new object,
# so the data is not wiped every time the user clicks a button.
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None          # holds the Owner instance

if "pet" not in st.session_state:
    st.session_state.pet = None            # holds the active Pet instance

if "task_counter" not in st.session_state:
    st.session_state.task_counter = 0      # used to generate unique task IDs

# ---------------------------------------------------------------------------
# Helper maps — convert human-readable UI labels to enum values
# ---------------------------------------------------------------------------
PRIORITY_MAP = {
    "High":   Priority.HIGH,
    "Medium": Priority.MEDIUM,
    "Low":    Priority.LOW,
}

CATEGORY_MAP = {
    "Walk":      TaskCategory.WALK,
    "Feeding":   TaskCategory.FEEDING,
    "Medication":TaskCategory.MEDICATION,
    "Enrichment":TaskCategory.ENRICHMENT,
    "Grooming":  TaskCategory.GROOMING,
    "Vet Visit": TaskCategory.VET_VISIT,
    "Play":      TaskCategory.PLAY,
}

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
        budget     = st.number_input(
            "Available minutes today",
            min_value=30, max_value=720, value=180,
            help="How many total minutes can you spend on pet care today?",
        )
        wake_time  = st.text_input(
            "Wake time (HH:MM)", value="07:00",
            help="This is when your schedule starts.",
        )

    with col_b:
        st.markdown("**Pet info**")
        pet_name = st.text_input("Pet name", value="Mochi")
        species  = st.selectbox("Species", ["dog", "cat", "other"])
        age      = st.number_input("Age (years)", min_value=0, max_value=30, value=3)

    profile_submitted = st.form_submit_button("Create / Update Profile", type="primary")

if profile_submitted:
    # Build fresh Owner and Pet objects and store them in session_state
    new_owner = Owner(
        name=owner_name,
        available_minutes=int(budget),
        wake_time=wake_time,
    )
    new_pet = Pet(name=pet_name, species=species, age=int(age))
    new_owner.add_pet(new_pet)

    st.session_state.owner        = new_owner
    st.session_state.pet          = new_pet
    st.session_state.task_counter = 0   # reset task IDs for fresh profile
    st.success(f"Profile saved! Owner: {owner_name}  |  Pet: {pet_name} ({species})")

# ===========================================================================
# SECTION 2 — Add Care Tasks
# (only shown once a profile exists)
# ===========================================================================
if st.session_state.pet is not None:
    st.divider()
    st.subheader("Step 2 - Add Care Tasks")
    st.caption(
        f"Adding tasks for **{st.session_state.pet.name}**. "
        "Each task will be considered by the scheduler."
    )

    with st.form("task_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            task_title   = st.text_input("Task title", value="Morning Walk")
            category_key = st.selectbox("Category", list(CATEGORY_MAP.keys()))

        with col2:
            duration     = st.number_input(
                "Duration (min)", min_value=1, max_value=240, value=20
            )
            priority_key = st.selectbox("Priority", list(PRIORITY_MAP.keys()))

        with col3:
            is_mandatory   = st.checkbox("Mandatory?", help="Mandatory tasks are always scheduled first.")
            preferred_time = st.text_input(
                "Preferred time (HH:MM)",
                value="",
                placeholder="optional",
                help="Leave blank if there is no preferred time.",
            )

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
        )
        st.session_state.pet.add_task(new_task)
        st.success(f"Added: {task_title} ({duration} min, {priority_key} priority)")

    # Display current task list
    current_tasks = st.session_state.pet.get_tasks()
    if current_tasks:
        st.markdown(f"**Tasks for {st.session_state.pet.name}** ({len(current_tasks)} total):")
        task_rows = [
            {
                "Title":          t.title,
                "Category":       t.category.value,
                "Duration (min)": t.duration_minutes,
                "Priority":       t.priority.name,
                "Mandatory":      "Yes" if t.is_mandatory else "No",
                "Preferred Time": t.preferred_time if t.preferred_time else "—",
            }
            for t in current_tasks
        ]
        st.dataframe(task_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No tasks yet. Add one above.")

# ===========================================================================
# SECTION 3 — Generate Daily Schedule
# (only shown once at least one task exists)
# ===========================================================================
if st.session_state.pet is not None and st.session_state.pet.get_tasks():
    st.divider()
    st.subheader("Step 3 - Generate Daily Schedule")
    st.caption(
        f"Owner: **{st.session_state.owner.name}**  |  "
        f"Budget: **{st.session_state.owner.available_minutes} min**  |  "
        f"Start: **{st.session_state.owner.wake_time}**"
    )

    if st.button("Generate Schedule", type="primary", use_container_width=True):
        today     = date.today().strftime("%Y-%m-%d")
        scheduler = Scheduler(owner=st.session_state.owner, pet=st.session_state.pet)
        plan      = scheduler.build_plan(date=today)

        # Summary banner
        st.success(plan.get_summary())

        # Scheduled tasks
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
                            f"{entry.reason}"
                        )

        # Skipped tasks
        if plan.skipped_tasks:
            st.markdown("#### Skipped Tasks")
            for skipped in plan.skipped_tasks:
                st.warning(
                    f"{skipped.task.title} ({skipped.task.duration_minutes} min) "
                    f"— {skipped.reason}"
                )