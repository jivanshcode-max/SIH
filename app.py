import json
import streamlit as st
import pandas as pd

# Load data
def load_data():
    with open("output.json", "r", encoding="utf-8") as f:
        return json.load(f)

data = load_data()
trains = data.get("trains", [])
last_clearance = data.get("last_section_clearance_time", "N/A")

st.set_page_config(page_title="Section Scheduling Results", layout="wide")

# Title
st.title("🚦 Train Section Scheduling Results")

# Subtitle
st.markdown(
    "<h4 style='color: #0047AB;'>Section-level Track Optimization Dashboard</h4>",
    unsafe_allow_html=True
)

# Convert to dataframe for tabular display
df = pd.DataFrame([
    {
        "Train ID": t["id"],
        "Train Name": t["train_name"],
        "Type": t.get("type", "").capitalize(),
        "Priority": t["priority"],
        "From": t["starting_station"],
        "To": t["destination_station"],
        "Section Entry": t["section_entry_time"],
        "Section Exit": t["section_exit_time"],
        "Track": t["assigned_track"],
    }
    for t in trains
])

st.dataframe(df, use_container_width=True)

# Train selector
train_names = [t["train_name"] for t in trains]
selected_train = st.selectbox("🔎 View details for a train:", train_names)

# Show details in section-level style
if selected_train:
    train = next(t for t in trains if t["train_name"] == selected_train)

    st.markdown("---")
    st.subheader(f"📌 Train Details: {train['train_name']}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Train ID:** {train['id']}")
        st.markdown(f"**Type:** {train.get('type', '').capitalize()}")
        st.markdown(f"**Priority:** {train['priority']}")
        st.markdown(f"**From:** {train['starting_station']}")
        st.markdown(f"**To:** {train['destination_station']}")
        st.markdown(f"**Days of Running:** {', '.join(train['days_of_running'])}")

    with col2:
        st.markdown(f"**Original Departure:** {train['departure_time']}")
        st.markdown(f"**Original Arrival:** {train['arrival_time']}")
        st.markdown(f"**Travel Time:** {train['travel_time']}")
        st.markdown(f"**Distance:** {train['total_distance']}")
        st.markdown(f"**Section Entry:** {train['section_entry_time']}")
        st.markdown(f"**Section Exit:** {train['section_exit_time']}")
        st.markdown(f"**Assigned Track:** {train['assigned_track']}")

    if train.get("classes_available"):
        st.markdown("### 🎟️ Fare Details")
        fares = pd.DataFrame.from_dict(train["fare_details"], orient="index", columns=["Fare"])
        fares.index.name = "Class"
        st.table(fares)

# Last section clearance at bottom
st.markdown("---")
st.markdown(
    f"<h4 style='color: green;'>✅ Last Section Clearance Time: {last_clearance}</h4>",
    unsafe_allow_html=True
)
