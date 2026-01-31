import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Pippafit Tracker", page_icon="💪")
# URL provided previously
SHEET_URL = "https://docs.google.com/spreadsheets/d/1wNtahXuCiVUUfSS_DuqpccR2s1y3EZE2IoEfgeFu0ig"

# --- LOAD MOVEMENT DATABASE (CSV) ---
try:
    # UPDATED: Reading from the new filename
    movements_db = pd.read_csv("Pippafit_data.csv")
except FileNotFoundError:
    st.error("Error: Pippafit_data.csv not found. Check your folder.")
    st.stop()

# --- CONNECT TO GOOGLE SHEET (LOGS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Read existing logs from 'Logs' tab
try:
    history_df = conn.read(spreadsheet=SHEET_URL, worksheet="Logs", usecols=[0, 1, 2, 3], ttl=0)
    if history_df.empty:
        history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])
except Exception:
    history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])

# --- UI LOGIC ---
st.title("Pippafit Tracker")

# 1. Day Selection
day_order = ['Monday', 'Wednesday', 'Saturday']
available_days = movements_db['Day'].unique()
# Sort available days: Mon/Wed/Sat first, others appended
sorted_days = sorted(available_days, key=lambda x: day_order.index(x) if x in day_order else 99)
selected_day = st.selectbox("Day", sorted_days)

# Filter: Day
day_moves = movements_db[movements_db['Day'] == selected_day]

# 2. Target Group Selection
groups = day_moves['Target Group'].unique()
selected_group = st.selectbox("Muscle Group", groups)

# Filter: Group
group_moves = day_moves[day_moves['Target Group'] == selected_group]

# 3. Exercise Selection (Core First)
core_row = group_moves[group_moves['Status'] == 'Core']
exercise_options = group_moves['Exercise'].tolist()

default_idx = 0
if not core_row.empty:
    core_name = core_row.iloc[0]['Exercise']
    if core_name in exercise_options:
        default_idx = exercise_options.index(core_name)

selected_exercise = st.selectbox("Exercise", exercise_options, index=default_idx)

# 4. Video Link
current_ex_data = group_moves[group_moves['Exercise'] == selected_exercise].iloc[0]
video_url = current_ex_data['Video Link']

if pd.notna(video_url) and str(video_url).startswith('http'):
    st.markdown(f"**[🎥 Watch Demo]({video_url})**")

# --- HISTORY & INPUT ---
st.divider()

# Filter history for THIS specific exercise
ex_history = history_df[history_df['Exercise'] == selected_exercise].copy()

# Determine Target
target_weight = 0.0
target_reps_msg = "No history"

if not ex_history.empty:
    ex_history['Date'] = pd.to_datetime(ex_history['Date'])
    last_log = ex_history.sort_values(by='Date').iloc[-1]
    target_weight = float(last_log['Weight'])
    target_reps_msg = f"{last_log['Reps']} reps"
    
    st.metric(
        label="TARGET (Last Session)",
        value=f"{target_weight} kg",
        delta=target_reps_msg
    )
else:
    st.info("No previous logs for this specific exercise.")

# Input Form
with st.form("log_form"):
    c1, c2 = st.columns(2)
    weight_in = c1.number_input("Weight (kg)", value=target_weight, step=1.25)
    reps_in = c2.number_input("Reps", value=8, step=1)
    
    if st.form_submit_button("LOG SET", type="primary"):
        new_row = pd.DataFrame([{
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Exercise": selected_exercise,
            "Weight": weight_in,
            "Reps": reps_in
        }])
        
        # Append locally
        updated_df = pd.concat([history_df, new_row], ignore_index=True)
        # Push to Google Sheet 'Logs' tab
        conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=updated_df)
        
        st.success(f"Logged {selected_exercise}!")
        st.rerun()

# Recent Logs Display
st.subheader("Session Logs")
st.dataframe(history_df.tail(5).iloc[::-1], hide_index=True)