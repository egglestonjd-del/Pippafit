import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Pippafit Tracker", page_icon="💪")
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- LOAD MOVEMENT DATABASE ---
try:
    movements_db = pd.read_csv("Pippafit_data.csv")
except FileNotFoundError:
    st.error("Error: Pippafit_data.csv not found. Ensure it is committed to GitHub.")
    st.stop()

# --- CONNECT TO GOOGLE SHEET ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Fetch existing logs
try:
    history_df = conn.read(spreadsheet=SHEET_URL, worksheet="Logs", usecols=[0, 1, 2, 3], ttl=0)
    # Ensure columns exist
    if history_df.empty:
        history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])
except Exception:
    history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])

# --- UI HEADER ---
st.title("Pippafit Tracker")

# 1. Day Selection
# Get unique days from CSV (maintains CSV order if possible, otherwise sorts)
available_days = movements_db['Day'].unique()
# Try to default to today's day if it's in the list
today_name = datetime.now().strftime("%A")
default_ix = 0
if today_name in available_days:
    default_ix = list(available_days).index(today_name)

selected_day = st.selectbox("Select Routine", available_days, index=default_ix)

# 2. Filter Exercises for the Day
todays_exercises = movements_db[movements_db['Day'] == selected_day]

if todays_exercises.empty:
    st.info(f"No exercises found for {selected_day}.")
else:
    st.write(f"**Routine for {selected_day}**")
    
    # --- RENDER EXERCISE BLOCKS ---
    for index, row in todays_exercises.iterrows():
        exercise = row['Exercise']
        
        # A. Get Target (Last Log)
        ex_history = history_df[history_df['Exercise'] == exercise].copy()
        last_weight = 0.0
        last_reps = 0
        target_msg = "No history"
        
        if not ex_history.empty:
            ex_history['Date'] = pd.to_datetime(ex_history['Date'], errors='coerce')
            ex_history = ex_history.sort_values(by='Date')
            last_entry = ex_history.iloc[-1]
            last_weight = float(last_entry['Weight'])
            last_reps = int(last_entry['Reps'])
            target_msg = f"Last: {last_weight}kg x {last_reps}"

        # B. Create the Block (Form)
        with st.form(key=f"form_{exercise}"):
            st.subheader(exercise)
            st.caption(target_msg)
            
            # Create 3 Sets of Inputs
            # Using columns for compact layout: [Weight] [Reps]
            
            # Set 1
            c1, c2 = st.columns([1, 1])
            w1 = c1.number_input("Set 1 Kg", value=last_weight, step=1.25, key=f"{exercise}_w1")
            r1 = c2.number_input("Set 1 Reps", value=8, step=1, key=f"{exercise}_r1")
            
            # Set 2
            c3, c4 = st.columns([1, 1])
            w2 = c3.number_input("Set 2 Kg", value=last_weight, step=1.25, key=f"{exercise}_w2")
            r2 = c4.number_input("Set 2 Reps", value=8, step=1, key=f"{exercise}_r2")
            
            # Set 3
            c5, c6 = st.columns([1, 1])
            w3 = c5.number_input("Set 3 Kg", value=last_weight, step=1.25, key=f"{exercise}_w3")
            r3 = c6.number_input("Set 3 Reps", value=8, step=1, key=f"{exercise}_r3")

            # Submit Button
            if st.form_submit_button(f"LOG {exercise.upper()}", type="primary"):
                # timestamp
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Prepare rows to add
                new_logs = []
                
                # Only add sets that have > 0 reps to avoid empty logs
                if r1 > 0:
                    new_logs.append({"Date": now_str, "Exercise": exercise, "Weight": w1, "Reps": r1})
                if r2 > 0:
                    new_logs.append({"Date": now_str, "Exercise": exercise, "Weight": w2, "Reps": r2})
                if r3 > 0:
                    new_logs.append({"Date": now_str, "Exercise": exercise, "Weight": w3, "Reps": r3})
                
                if new_logs:
                    new_df = pd.DataFrame(new_logs)
                    updated_df = pd.concat([history_df, new_df], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=updated_df)
                    st.success(f"Logged 3 sets for {exercise}!")
                    st.rerun() # Refresh to update targets