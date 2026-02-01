import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import base64

# --- CONFIG ---
st.set_page_config(page_title="Pippafit 65", page_icon="💪")
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- HELPER: IMAGE TO BASE64 ---
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None

# --- CUSTOM CSS ---
hide_st_style = """
    <style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
    .block-container {padding-top: 2rem;}
    
    .logo-container {
        margin-bottom: 50px;
        display: flex;
        justify-content: center;
    }
    .logo-light { display: block; margin: auto; width: 250px; }
    .logo-dark { display: none; margin: auto; width: 250px; }
    
    @media (prefers-color-scheme: dark) {
        .logo-light { display: none; }
        .logo-dark { display: block; }
    }
    
    div.stButton > button[kind="primary"] {
        background-color: #D81B60 !important;
        border-color: #D81B60 !important;
        color: white !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #AD1457 !important;
        border-color: #AD1457 !important;
    }

    .stNumberInput input {
        font-weight: bold;
        background-color: transparent;
    }
    div[data-testid="stNumberInput"] {
        border: 1px solid #d0d0d0;
        border-radius: 8px;
        box-shadow: 0px 1px 3px rgba(0,0,0,0.05);
        padding: 2px;
    }
    
    [data-baseweb="tab-list"] {
        width: 100%;
        display: flex;
    }
    button[data-baseweb="tab"]:nth-of-type(1) {
        width: 80% !important;
        justify-content: flex-start !important;
        font-size: 18px !important;
        font-weight: 800 !important;
        padding-left: 10px !important;
    }
    button[data-baseweb="tab"]:nth-of-type(2) {
        width: 20% !important;
        justify-content: flex-end !important;
        font-size: 14px !important;
        padding-right: 10px !important;
        color: #888; 
    }

    input[aria-label="W"], input[aria-label="R"] {
        color: #b36b00 !important;              
    }
    div[data-testid="stNumberInput"]:has(input[aria-label="W"]),
    div[data-testid="stNumberInput"]:has(input[aria-label="R"]) {
        border: 2px solid #ffbd45 !important;   
        background-color: #fffbf0 !important;   
    }
    
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

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

# --- CONNECT TO SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    movements_db = conn.read(spreadsheet=SHEET_URL, worksheet="Exercise_bank", ttl=0)
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

try:
    history_df = conn.read(spreadsheet=SHEET_URL, worksheet="Logs", usecols=[0, 1, 2, 3], ttl=0)
    if history_df.empty: 
        history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])
except Exception:
    history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])

# --- UI HEADER ---
img_light = get_base64_image("Pippafit_Light.png")
img_dark = get_base64_image("Pippafit_Dark.png")

if img_light and img_dark:
    st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{img_light}" class="logo-light"><img src="data:image/png;base64,{img_dark}" class="logo-dark"></div>', unsafe_allow_html=True)
else:
    st.title("Pippafit 65") 

# --- DAY SELECTION ---
if 'selected_day' not in st.session_state:
    today_name = datetime.now().strftime("%A")
    st.session_state.selected_day = today_name if today_name in ["Monday", "Wednesday", "Saturday"] else "Monday"

col_mon, col_wed, col_sat = st.columns(3)
if col_mon.button("Monday", type="primary" if st.session_state.selected_day == "Monday" else "secondary", use_container_width=True):
    st.session_state.selected_day = "Monday"
    st.rerun()
if col_wed.button("Wednesday", type="primary" if st.session_state.selected_day == "Wednesday" else "secondary", use_container_width=True):
    st.session_state.selected_day = "Wednesday"
    st.rerun()
if col_sat.button("Saturday", type="primary" if st.session_state.selected_day == "Saturday" else "secondary", use_container_width=True):
    st.session_state.selected_day = "Saturday"
    st.rerun()

# --- FILTER CONTENT ---
day_data = movements_db[movements_db['Day'] == st.session_state.selected_day]

if day_data.empty:
    st.info(f"No exercises found for {st.session_state.selected_day}.")
else:
    target_groups = list(dict.fromkeys(day_data['Target Group']))
    
    for group in target_groups:
        with st.container(border=True):
            group_options = day_data[day_data['Target Group'] == group]
            exercise_list = group_options['Exercise'].tolist()
            
            # SESSION STATE TRACKING FOR SWAPS
            sb_key = f"select_{group}_{st.session_state.selected_day}"
            current_exercise = st.session_state.get(sb_key, exercise_list[0])
            
            # HEADER: DISPLAY CURRENT EXERCISE NAME
            st.markdown(f"### {current_exercise}") 
            
            # DROPDOWN: LABELLED "Swap exercise"
            selected_exercise = st.selectbox("Swap exercise", exercise_list, index=exercise_list.index(current_exercise) if current_exercise in exercise_list else 0, key=sb_key)

            current_exercise_row = group_options[group_options['Exercise'] == selected_exercise]
            if not current_exercise_row.empty:
                video_url = current_exercise_row.iloc[0]['Video Link']
                if pd.notna(video_url) and str(video_url).startswith("http"):
                    with st.expander("▶️ Exercise tutorial"):
                        st.video(video_url)

            # HISTORY / TARGET TO BEAT
            ex_history = history_df[history_df['Exercise'] == selected_exercise].copy()
            target_msg = "No history"
            if not ex_history.empty:
                ex_history['Date'] = pd.to_datetime(ex_history['Date'], errors='coerce')
                last_date = ex_history.sort_values(by='Date').iloc[-1]['Date']
                last_session = ex_history[ex_history['Date'].dt.date == last_date.date()]
                if not last_session.empty:
                    best_set = last_session.sort_values(by=['Weight', 'Reps'], ascending=True).iloc[-1]
                    target_msg = f"Target to beat: {float(best_set['Weight'])}kg x {int(best_set['Reps'])}"
                
            tab_log, tab_edit = st.tabs(["Exercise", "Edit"])

            with tab_log:
                st.caption(f"**{target_msg}**")
                k_w1, k_r1 = f"{selected_exercise}_w1", f"{selected_exercise}_r1"
                k_w2, k_r2 = f"{selected_exercise}_w2", f"{selected_exercise}_r2"
                k_w3, k_r3 = f"{selected_exercise}_w3", f"{selected_exercise}_r3"

                for i, (kw, kr) in enumerate([(k_w1, k_r1), (k_w2, k_r2), (k_w3, k_r3)], 1):
                    with st.container(border=True):
                        st.markdown(f"**Set {i}**")
                        c_w, c_r = st.columns(2, gap="small")
                        c_w.number_input("Kg", value=None, step=1.25, key=kw, on_change=update_weights if i==1 else None, args=(selected_exercise,) if i==1 else None)
                        c_r.number_input("Reps", value=None, step=1, key=kr)

                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.button("SAVE SETS", type="primary", key=f"btn_{selected_exercise}_{group}", use_container_width=True):
                    logs = []
                    for kw, kr in [(k_w1, k_r1), (k_w2, k_r2), (k_w3, k_r3)]:
                        w, r = st.session_state.get(kw), st.session_state.get(kr)
                        if r: logs.append({"Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Exercise": selected_exercise, "Weight": w or 0, "Reps": r})
                    if logs:
                        conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=pd.concat([history_df, pd.DataFrame(logs)], ignore_index=True))
                        st.toast("Saved!", icon="✅")
                        st.rerun()

            with tab_edit:
                recent_logs = history_df[history_df['Exercise'] == selected_exercise].sort_values(by='Date', ascending=False).head(5)
                if recent_logs.empty: st.info("No logs.")
                else:
                    for idx, row in recent_logs.iterrows():
                        st.caption(f"**{pd.to_datetime(row['Date']).strftime('%b %d %H:%M')}**")
                        hc1, hc2, hc3, hc4 = st.columns([1.5, 1.5, 0.7, 0.7])
                        nw, nr = hc1.number_input("W", value=float(row['Weight']), step=1.25, key=f"ew_{idx}"), hc2.number_input("R", value=int(row['Reps']), step=1, key=f"er_{idx}")
                        if hc3.button("💾", key=f"s_{idx}"):
                            history_df.at[idx, 'Weight'], history_df.at[idx, 'Reps'] = nw, nr
                            conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=history_df)
                            st.rerun()
                        if hc4.button("❌", key=f"d_{idx}"):
                            conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=history_df.drop(idx))
                            st.rerun()

    st.divider()
    if st.button("Complete workout", type="primary", use_container_width=True):
        st.balloons()
        st.success("Workout logged successfully!")