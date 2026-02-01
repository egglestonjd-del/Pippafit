import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Pippafit Tracker", page_icon="💪")
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- REMOVE STREAMLIT BRANDING (CTAs) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- THEME MANAGEMENT ---
if 'theme' not in st.session_state:
    st.session_state.theme = 'system'

# Apply CSS based on session state
if st.session_state.theme == 'dark':
    st.markdown("""
        <style>
            [data-testid="stAppViewContainer"] {
                background-color: #0e1117;
                color: #fafafa;
            }
            [data-testid="stHeader"] {
                background-color: #0e1117;
            }
            [data-testid="stSidebar"] {
                background-color: #262730;
            }
            .stSelectbox > div > div {
                background-color: #262730;
                color: #fafafa;
            }
            .stNumberInput input {
                color: #fafafa;
            }
        </style>
        """, unsafe_allow_html=True)

elif st.session_state.theme == 'light':
    st.markdown("""
        <style>
            [data-testid="stAppViewContainer"] {
                background-color: #ffffff;
                color: #31333F;
            }
            [data-testid="stHeader"] {
                background-color: #ffffff;
            }
            [data-testid="stSidebar"] {
                background-color: #f0f2f6;
            }
        </style>
        """, unsafe_allow_html=True)

# --- HEADER LAYOUT (TITLE + TOGGLE) ---
col_title, col_toggle = st.columns([6, 1], gap="small")

with col_title:
    st.title("Pippafit Tracker")

with col_toggle:
    # Button Logic:
    # If currently Dark -> Show Sun (to switch to Light)
    # If currently Light or System -> Show Moon (to switch to Dark)
    if st.session_state.theme == 'dark':
        if st.button("☀️", key="theme_btn", help="Switch to Light Mode"):
            st.session_state.theme = 'light'
            st.rerun()
    else:
        if st.button("🌙", key="theme_btn", help="Switch to Dark Mode"):
            st.session_state.theme = 'dark'
            st.rerun()

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
    if history_df.empty:
        history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])
except Exception:
    history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])

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

        # --- VIDEO DISPLAY ---
        current_exercise_row = group_options[group_options['Exercise'] == selected_exercise]
        
        if not current_exercise_row.empty:
            video_url = current_exercise_row.iloc[0]['Video Link']
            if pd.notna(video_url) and str(video_url).startswith("http"):
                with st.expander("▶️ Watch Tutorial"):
                    st.video(video_url)

        # --- DATA PREP ---
        ex_history = history_df[history_df['Exercise'] == selected_exercise].copy()
        last_weight = 0.0
        target_msg = "No history"
        
        if not ex_history.empty:
            ex_history['Date'] = pd.to_datetime(ex_history['Date'], errors='coerce')
            ex_history = ex_history.sort_values(by='Date')
            
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
                    updated_df = pd.concat([history_df, new_df], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=updated_df)
                    st.success(f"Logged {selected_exercise}!")
                    st.rerun()

        # --- MANAGE HISTORY ---
        with st.expander(f"Manage History: {selected_exercise}"):
            recent_logs = history_df[history_df['Exercise'] == selected_exercise].sort_values(by='Date', ascending=False).head(5)
            
            if recent_logs.empty:
                st.caption("No logs found.")
            else:
                for idx, row in recent_logs.iterrows():
                    d_str = pd.to_datetime(row['Date']).strftime("%b %d %H:%M")
                    display_text = f"{d_str} | **{row['Weight']}kg** x {row['Reps']}"
                    
                    col_txt, col_btn = st.columns([4, 1])
                    with col_txt:
                        st.markdown(display_text)
                    with col_btn:
                        if st.button("❌", key=f"del_{idx}"):
                            history_df = history_df.drop(idx)
                            conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=history_df)
                            st.toast(f"Deleted entry!", icon="🗑️")
                            st.rerun()

        st.divider()