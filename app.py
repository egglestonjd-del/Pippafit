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
    # We read the sheet into a DataFrame. The 'index' of this DF corresponds to the row number.
    history_df = conn.read(spreadsheet=SHEET_URL, worksheet="Logs", usecols=[0, 1, 2, 3], ttl=0)
    if history_df.empty:
        history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])
except Exception:
    history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])

# --- UI HEADER ---
st.title("Pippafit Tracker")

# 1. Day Selection
available_days = movements_db['Day'].unique()
today_name = datetime.now().strftime("%A")
default_ix = 0
if today_name in available_days:
    default_ix = list(available_days).index(today_name)

selected_day = st.selectbox("Select Routine", available_days, index=default_ix)

# 2. Filter Logic: Group by Target Muscle
day_data = movements_db[movements_db['Day'] == selected_day]

if day_data.empty:
    st.info(f"No exercises found for {selected_day}.")
else:
    st.write(f"**Routine for {selected_day}**")
    
    # Get unique Target Groups
    target_groups = list(dict.fromkeys(day_data['Target Group']))
    
    for group in target_groups:
        group_options = day_data[day_data['Target Group'] == group]
        exercise_list = group_options['Exercise'].tolist()
        
        st.markdown(f"### {group}") 
        
        # Dropdown
        selected_exercise = st.selectbox(
            "Select Movement", 
            exercise_list, 
            index=0, 
            key=f"select_{group}_{selected_day}",
            label_visibility="collapsed"
        )

        # --- DATA PREP ---
        # Get History & Determine "Target to Beat"
        ex_history = history_df[history_df['Exercise'] == selected_exercise].copy()
        last_weight = 0.0
        target_msg = "No history"
        
        if not ex_history.empty:
            ex_history['Date'] = pd.to_datetime(ex_history['Date'], errors='coerce')
            ex_history = ex_history.sort_values(by='Date')
            
            # Find stats from the LAST session only
            last_date = ex_history.iloc[-1]['Date']
            last_session_df = ex_history[ex_history['Date'].dt.date == last_date.date()]
            best_set = last_session_df.sort_values(by=['Weight', 'Reps'], ascending=True).iloc[-1]
            
            last_weight = float(best_set['Weight'])
            last_reps = int(best_set['Reps'])
            target_msg = f"Target to beat: {last_weight}kg x {last_reps}"
            
        # --- LOGGING FORM ---
        with st.form(key=f"form_{selected_exercise}"):
            st.caption(f"**{target_msg}**")
            
            # 3 Sets Inputs
            c1, c2 = st.columns([1, 1])
            w1 = c1.number_input("Set 1 Kg", value=last_weight, step=1.25, key=f"{selected_exercise}_w1")
            r1 = c2.number_input("Set 1 Reps", value=8, step=1, key=f"{selected_exercise}_r1")
            
            c3, c4 = st.columns([1, 1])
            w2 = c3.number_input("Set 2 Kg", value=last_weight, step=1.25, key=f"{selected_exercise}_w2")
            r2 = c4.number_input("Set 2 Reps", value=8, step=1, key=f"{selected_exercise}_r2")
            
            c5, c6 = st.columns([1, 1])
            w3 = c5.number_input("Set 3 Kg", value=last_weight, step=1.25, key=f"{selected_exercise}_w3")
            r3 = c6.number_input("Set 3 Reps", value=8, step=1, key=f"{selected_exercise}_r3")

            # Submit
            if st.form_submit_button(f"LOG {selected_exercise.upper()}", type="primary"):
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_logs = []
                
                if r1 > 0: new_logs.append({"Date": now_str, "Exercise": selected_exercise, "Weight": w1, "Reps": r1})
                if r2 > 0: new_logs.append({"Date": now_str, "Exercise": selected_exercise, "Weight": w2, "Reps": r2})
                if r3 > 0: new_logs.append({"Date": now_str, "Exercise": selected_exercise, "Weight": w3, "Reps": r3})
                
                if new_logs:
                    new_df = pd.DataFrame(new_logs)
                    # Append new logs to the master DF
                    updated_df = pd.concat([history_df, new_df], ignore_index=True)
                    # Update Google Sheet
                    conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=updated_df)
                    st.success(f"Logged {selected_exercise}!")
                    st.rerun()

        # --- MANAGE HISTORY (DELETE FUNCTION) ---
        with st.expander(f"Manage History: {selected_exercise}"):
            # We filter for this exercise, but we keep the original Index so we know which row to delete
            recent_logs = history_df[history_df['Exercise'] == selected_exercise].sort_values(by='Date', ascending=False).head(5)
            
            if recent_logs.empty:
                st.caption("No logs found.")
            else:
                for idx, row in recent_logs.iterrows():
                    # Format: "Jan 01 12:30 | 50kg x 10"
                    d_str = pd.to_datetime(row['Date']).strftime("%b %d %H:%M")
                    display_text = f"{d_str} | **{row['Weight']}kg** x {row['Reps']}"
                    
                    # Layout: Text on left, Delete button on right
                    col_txt, col_btn = st.columns([4, 1])
                    with col_txt:
                        st.markdown(display_text)
                    with col_btn:
                        # Unique key is crucial here
                        if st.button("❌", key=f"del_{idx}"):
                            # Drop the row from the master dataframe using its index
                            history_df = history_df.drop(idx)
                            # Push the entire updated dataframe back to Google Sheets
                            conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=history_df)
                            st.toast(f"Deleted entry!", icon="🗑️")
                            st.rerun()

        st.divider()