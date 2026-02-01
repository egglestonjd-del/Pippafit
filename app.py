import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Pippafit 65", page_icon="💪")
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- CUSTOM CSS: HIDE BRANDING ---
hide_st_style = """
    <style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
    .block-container {padding-top: 2rem;}
    
    /* Make inputs distinct */
    .stNumberInput input {
        font-weight: bold;
    }
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- CELEBRATION LOGIC ---
if "celebrate" not in st.session_state:
    st.session_state.celebrate = False

if st.session_state.celebrate:
    st.balloons()
    st.toast("Great Set! Logged successfully.", icon="🎉")
    st.session_state.celebrate = False 

# --- AUTO-FILL CALLBACK ---
def update_weights(ex_key):
    """
    Called when Set 1 Weight changes. 
    Copies Set 1 value to Set 2 & 3 only if they are empty.
    """
    w1_key = f"{ex_key}_w1"
    w2_key = f"{ex_key}_w2"
    w3_key = f"{ex_key}_w3"
    
    val_w1 = st.session_state.get(w1_key)
    val_w2 = st.session_state.get(w2_key)
    val_w3 = st.session_state.get(w3_key)
    
    if val_w1 is not None:
        # If Set 2 is empty, fill it
        if val_w2 is None:
            st.session_state[w2_key] = val_w1
        # If Set 3 is empty, fill it
        if val_w3 is None:
            st.session_state[w3_key] = val_w1

# --- LOAD DATABASE ---
try:
    movements_db = pd.read_csv("Pippafit_data.csv")
except FileNotFoundError:
    st.error("Error: Pippafit_data.csv not found.")
    st.stop()

# --- CONNECT TO SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    history_df = conn.read(spreadsheet=SHEET_URL, worksheet="Logs", usecols=[0, 1, 2, 3], ttl=0)
    if history_df.empty: history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])
except Exception:
    history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])

# --- UI HEADER ---
st.title("Pippafit 65")

# 1. Day Selection
available_days = movements_db['Day'].unique()
today_name = datetime.now().strftime("%A")
default_ix = 0
if today_name in available_days:
    default_ix = list(available_days).index(today_name)

selected_day = st.selectbox("Select Routine", available_days, index=default_ix)

# 2. Filter Logic
day_data = movements_db[movements_db['Day'] == selected_day]

if day_data.empty:
    st.info(f"No exercises found for {selected_day}.")
else:
    st.write(f"**Routine for {selected_day}**")
    
    target_groups = list(dict.fromkeys(day_data['Target Group']))
    
    for group in target_groups:
        group_options = day_data[day_data['Target Group'] == group]
        exercise_list = group_options['Exercise'].tolist()
        
        st.markdown(f"### {group}") 
        
        selected_exercise = st.selectbox(
            "Select Movement", 
            exercise_list, 
            index=0, 
            key=f"select_{group}_{selected_day}",
            label_visibility="collapsed"
        )

        # Video
        current_exercise_row = group_options[group_options['Exercise'] == selected_exercise]
        if not current_exercise_row.empty:
            video_url = current_exercise_row.iloc[0]['Video Link']
            if pd.notna(video_url) and str(video_url).startswith("http"):
                with st.expander("▶️ Watch Tutorial"):
                    st.video(video_url)

        # History / Target
        ex_history = history_df[history_df['Exercise'] == selected_exercise].copy()
        target_msg = "No history"
        
        if not ex_history.empty:
            ex_history['Date'] = pd.to_datetime(ex_history['Date'], errors='coerce')
            last_date = ex_history.sort_values(by='Date').iloc[-1]['Date']
            last_session = ex_history[ex_history['Date'].dt.date == last_date.date()]
            best_set = last_session.sort_values(by=['Weight', 'Reps'], ascending=True).iloc[-1]
            target_msg = f"Target to beat: {float(best_set['Weight'])}kg x {int(best_set['Reps'])}"
            
        st.caption(f"**{target_msg}**")

        # --- LOGGING INPUTS (NO FORM for real-time updates) ---
        # Keys for session state
        k_w1, k_r1 = f"{selected_exercise}_w1", f"{selected_exercise}_r1"
        k_w2, k_r2 = f"{selected_exercise}_w2", f"{selected_exercise}_r2"
        k_w3, k_r3 = f"{selected_exercise}_w3", f"{selected_exercise}_r3"

        # Set 1
        # Added gap="medium" for visual separation
        c1, c2 = st.columns([1, 1], gap="medium")
        # Set 1 Weight triggers the auto-fill callback
        c1.number_input("Set 1 | Enter weight", value=None, step=1.25, key=k_w1, on_change=update_weights, args=(selected_exercise,))
        c2.number_input("Set 1 | Reps", value=None, step=1, key=k_r1)
        
        # Set 2
        c3, c4 = st.columns([1, 1], gap="medium")
        c3.number_input("Set 2 | Enter weight", value=None, step=1.25, key=k_w2)
        c4.number_input("Set 2 | Reps", value=None, step=1, key=k_r2)
        
        # Set 3
        c5, c6 = st.columns([1, 1], gap="medium")
        c5.number_input("Set 3 | Enter weight", value=None, step=1.25, key=k_w3)
        c6.number_input("Set 3 | Reps", value=None, step=1, key=k_r3)

        # Button (Manual Handling)
        if st.button(f"LOG {selected_exercise.upper()}", type="primary", key=f"btn_{selected_exercise}"):
            # Retrieve values from session state
            w1 = st.session_state.get(k_w1)
            r1 = st.session_state.get(k_r1)
            w2 = st.session_state.get(k_w2)
            r2 = st.session_state.get(k_r2)
            w3 = st.session_state.get(k_w3)
            r3 = st.session_state.get(k_r3)

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_logs = []

            # Check validity (Must have at least Reps to count as a set)
            if r1 is not None and r1 > 0:
                new_logs.append({"Date": now_str, "Exercise": selected_exercise, "Weight": w1 if w1 else 0, "Reps": r1})
            if r2 is not None and r2 > 0:
                new_logs.append({"Date": now_str, "Exercise": selected_exercise, "Weight": w2 if w2 else 0, "Reps": r2})
            if r3 is not None and r3 > 0:
                new_logs.append({"Date": now_str, "Exercise": selected_exercise, "Weight": w3 if w3 else 0, "Reps": r3})
            
            if new_logs:
                new_df = pd.DataFrame(new_logs)
                updated_df = pd.concat([history_df, new_df], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=updated_df)
                st.session_state.celebrate = True
                st.rerun()

        # Manage History
        with st.expander(f"Manage History: {selected_exercise}"):
            recent_logs = history_df[history_df['Exercise'] == selected_exercise].sort_values(by='Date', ascending=False).head(5)
            if recent_logs.empty:
                st.caption("No logs found.")
            else:
                for idx, row in recent_logs.iterrows():
                    d_str = pd.to_datetime(row['Date']).strftime("%b %d %H:%M")
                    display_text = f"{d_str} | **{row['Weight']}kg** x {row['Reps']}"
                    col_txt, col_btn = st.columns([4, 1])
                    with col_txt: st.markdown(display_text)
                    with col_btn:
                        if st.button("❌", key=f"del_{idx}"):
                            history_df = history_df.drop(idx)
                            conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=history_df)
                            st.toast(f"Deleted entry!", icon="🗑️")
                            st.rerun()

        st.divider()