import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Pippafit 65", page_icon="💪")
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- CUSTOM CSS ---
hide_st_style = """
    <style>
    /* 1. HIDE BRANDING */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
    .block-container {padding-top: 2rem;}
    
    /* 2. GENERAL INPUT STYLING */
    .stNumberInput input {
        font-weight: bold;
    }
    
    /* 3. TABS STYLING (The 80/20 Split) */
    
    /* Target the container of the tabs to ensure they span full width */
    [data-baseweb="tab-list"] {
        width: 100%;
        display: flex;
    }

    /* TAB 1: "Exercise" */
    button[data-baseweb="tab"]:nth-of-type(1) {
        width: 80% !important;
        justify-content: flex-start !important; /* Left Align */
        font-size: 18px !important;
        font-weight: 800 !important;
        padding-left: 10px !important;
    }

    /* TAB 2: "Edit" */
    button[data-baseweb="tab"]:nth-of-type(2) {
        width: 20% !important;
        justify-content: flex-end !important; /* Right Align */
        font-size: 14px !important;
        padding-right: 10px !important;
        color: #888; /* Slightly dimmer to de-emphasize */
    }

    /* 4. EDIT MODE STYLING (The Yellow Border) */
    input[aria-label="W"], input[aria-label="R"] {
        border: 2px solid #ffbd45 !important;   
        background-color: #fffbf0 !important;   
        color: #b36b00 !important;              
    }
    
    div[data-testid="stNumberInput"]:has(input[aria-label="W"]),
    div[data-testid="stNumberInput"]:has(input[aria-label="R"]) {
        border-radius: 5px;
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
    w1_key = f"{ex_key}_w1"
    w2_key = f"{ex_key}_w2"
    w3_key = f"{ex_key}_w3"
    val_w1 = st.session_state.get(w1_key)
    val_w2 = st.session_state.get(w2_key)
    val_w3 = st.session_state.get(w3_key)
    if val_w1 is not None:
        if val_w2 is None: st.session_state[w2_key] = val_w1
        if val_w3 is None: st.session_state[w3_key] = val_w1

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

        # History / Target Calculation
        ex_history = history_df[history_df['Exercise'] == selected_exercise].copy()
        target_msg = "No history"
        
        if not ex_history.empty:
            ex_history['Date'] = pd.to_datetime(ex_history['Date'], errors='coerce')
            last_date = ex_history.sort_values(by='Date').iloc[-1]['Date']
            last_session = ex_history[ex_history['Date'].dt.date == last_date.date()]
            best_set = last_session.sort_values(by=['Weight', 'Reps'], ascending=True).iloc[-1]
            target_msg = f"Target to beat: {float(best_set['Weight'])}kg x {int(best_set['Reps'])}"
            
        # --- TAB INTERFACE ---
        # Renamed 'Log' to 'Exercise'
        tab_log, tab_edit = st.tabs(["Exercise", "Edit"])

        # --- TAB 1: EXERCISE (Clean / Standard) ---
        with tab_log:
            st.caption(f"**{target_msg}**")
            
            k_w1, k_r1 = f"{selected_exercise}_w1", f"{selected_exercise}_r1"
            k_w2, k_r2 = f"{selected_exercise}_w2", f"{selected_exercise}_r2"
            k_w3, k_r3 = f"{selected_exercise}_w3", f"{selected_exercise}_r3"

            # Set 1
            c1, c2 = st.columns([1, 1], gap="medium")
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

            # LOG Button
            if st.button(f"LOG {selected_exercise.upper()}", type="primary", key=f"btn_{selected_exercise}"):
                w1, r1 = st.session_state.get(k_w1), st.session_state.get(k_r1)
                w2, r2 = st.session_state.get(k_w2), st.session_state.get(k_r2)
                w3, r3 = st.session_state.get(k_w3), st.session_state.get(k_r3)

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_logs = []

                if r1 is not None and r1 > 0: new_logs.append({"Date": now_str, "Exercise": selected_exercise, "Weight": w1 if w1 else 0, "Reps": r1})
                if r2 is not None and r2 > 0: new_logs.append({"Date": now_str, "Exercise": selected_exercise, "Weight": w2 if w2 else 0, "Reps": r2})
                if r3 is not None and r3 > 0: new_logs.append({"Date": now_str, "Exercise": selected_exercise, "Weight": w3 if w3 else 0, "Reps": r3})
                
                if new_logs:
                    new_df = pd.DataFrame(new_logs)
                    updated_df = pd.concat([history_df, new_df], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=updated_df)
                    st.session_state.celebrate = True
                    st.rerun()

        # --- TAB 2: EDIT HISTORY (Yellow/Warning Style) ---
        with tab_edit:
            recent_logs = history_df[history_df['Exercise'] == selected_exercise].sort_values(by='Date', ascending=False).head(5)
            
            if recent_logs.empty:
                st.info("No logs to edit.")
            else:
                st.caption("📝 **Editing past entries**")
                for idx, row in recent_logs.iterrows():
                    d_str = pd.to_datetime(row['Date']).strftime("%b %d %H:%M")
                    st.caption(f"**{d_str}**")
                    
                    # Columns: Weight | Reps | Save | Delete
                    hc1, hc2, hc3, hc4 = st.columns([1.5, 1.5, 0.7, 0.7], gap="small")
                    
                    # Edit Inputs
                    new_w = hc1.number_input("W", value=float(row['Weight']), step=1.25, key=f"edit_w_{idx}", label_visibility="collapsed")
                    new_r = hc2.number_input("R", value=int(row['Reps']), step=1, key=f"edit_r_{idx}", label_visibility="collapsed")
                    
                    # Update Button
                    if hc3.button("💾", key=f"save_{idx}", help="Save Changes"):
                        history_df.at[idx, 'Weight'] = new_w
                        history_df.at[idx, 'Reps'] = new_r
                        conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=history_df)
                        st.toast("Entry Updated!", icon="✅")
                        st.rerun()

                    # Delete Button
                    if hc4.button("❌", key=f"del_{idx}", help="Delete Entry"):
                        history_df = history_df.drop(idx)
                        conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=history_df)
                        st.toast("Deleted!", icon="🗑️")
                        st.rerun()
                    
                    st.divider()

        st.divider()