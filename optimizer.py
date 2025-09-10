import json
from datetime import datetime, timedelta
from ortools.sat.python import cp_model

# --------------------------
# Helpers
# --------------------------
def parse_time_to_minutes(time_str: str) -> int:
    """Convert HH:MM into total minutes from midnight."""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m

def minutes_to_clock(minutes: int) -> str:
    """Convert minutes from midnight into clock time string (12-hour format)."""
    base_time = datetime.strptime("00:00", "%H:%M")
    new_time = base_time + timedelta(minutes=minutes)
    return new_time.strftime("%I:%M %p")

# --------------------------
# Load Input
# --------------------------
with open("dataset.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

tracks = raw_data["junction"]["tracks"]      # List of tracks with length_km and speed_kmph
trains = raw_data["trains"]                 # List of trains

# Compute travel times per track and arrival in minutes
for t in trains:
    durations = []
    for tr in tracks:
        time_min = int((tr["length_km"] / tr["speed_kmph"]) * 60)
        durations.append(time_min)
    t["durations"] = durations
    t["arrival_min"] = parse_time_to_minutes(t["arrival_time"])

# --------------------------
# Build CP-SAT Model
# --------------------------
model = cp_model.CpModel()

# Dynamic horizon: latest arrival + longest run + buffer
latest_arrival = max(t["arrival_min"] for t in trains)
longest_run = max(max(t["durations"]) for t in trains)
horizon = latest_arrival + longest_run + 600  # buffer for queuing

start_vars = {}
end_vars = {}
track_assignments = {}
track_intervals = [[] for _ in tracks]

for t in trains:
    name = t["train_name"]
    start = model.NewIntVar(0, horizon, f"start_{name}")
    end = model.NewIntVar(0, horizon, f"end_{name}")
    start_vars[name] = start
    end_vars[name] = end

    # Train cannot enter before arrival
    model.Add(start >= t["arrival_min"])

    track_bools = []
    end_candidates = []

    for tr_id, tr in enumerate(tracks):
        b = model.NewBoolVar(f"{name}_on_track{tr_id}")
        duration = t["durations"][tr_id]

        interval = model.NewOptionalIntervalVar(start, duration, end, b, f"{name}_track{tr_id}")
        track_intervals[tr_id].append(interval)
        track_bools.append(b)

        end_candidate = model.NewIntVar(0, horizon, f"{name}_end_track{tr_id}")
        model.Add(end_candidate == start + duration).OnlyEnforceIf(b)
        end_candidates.append(end_candidate)

    # Train must be assigned to exactly one track
    model.Add(sum(track_bools) == 1)
    model.AddMaxEquality(end, end_candidates)
    track_assignments[name] = track_bools

# Prevent overlaps on each track
for tr_id in range(len(tracks)):
    model.AddNoOverlap(track_intervals[tr_id])

# --------------------------
# Objective
# --------------------------
# last_end represents latest train leaving the section
last_section_exit = model.NewIntVar(0, horizon, "last_section_exit")
model.AddMaxEquality(last_section_exit, [end_vars[t["train_name"]] for t in trains])

# Weighted completion to prioritize important trains (lower priority number = higher importance)
weighted_completion = []
for t in trains:
    weight = 10 - t["priority"]  # express=1 gets higher weight
    weighted_completion.append(weight * end_vars[t["train_name"]])

model.Minimize(sum(weighted_completion))

# --------------------------
# Solve
# --------------------------
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 10
status = solver.Solve(model)

# --------------------------
# Output
# --------------------------
output_data = {"trains": [], "last_section_clearance_time": None}

if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    for t in trains:
        name = t["train_name"]
        s = solver.Value(start_vars[name])
        e = solver.Value(end_vars[name])
        chosen_track = [tr for tr, b in enumerate(track_assignments[name]) if solver.Value(b) == 1][0]

        enriched = t.copy()
        enriched.update({
            "section_entry_time": minutes_to_clock(s),
            "section_exit_time": minutes_to_clock(e),
            "assigned_track": chosen_track + 1  # Track 1/2 instead of 0/1
        })
        output_data["trains"].append(enriched)

    output_data["last_section_clearance_time"] = minutes_to_clock(solver.Value(last_section_exit))

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("Section schedule saved to output.json")
else:
    print("No feasible solution found.")
