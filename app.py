import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import base64
import re

# --- CONFIG ---
st.set_page_config(page_title="Pippafit 65", page_icon="💪")
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- HELPER: CONVERT SHORTS TO STANDARD URL ---
def format_youtube_url(url):
    if not isinstance(url, str):
        return url
    if "/shorts/" in url:
        return url.replace("/shorts/", "/watch?v=")
    return url

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

    .stNumberInput input {
        font-weight: bold;
    }
    div[data-testid="stNumberInput"] {
        border: 1px solid #d0d0d0;
        border-radius: 8px;
        padding: 2px;
    }
    
    .muscle-header {
        color: #888;
        font-size: 0.75rem;
        text-transform: uppercase;
        font-weight: bold;
        margin-bottom: 5px;
    }

    .exercise-title {
        font-size: 1.4rem;
        font-weight: 800;
        margin-bottom: 10px;
        line-height: 1.2;
    }

    /* INLINE SELECTBOX CSS */
    div[data-testid="stSelectbox"] > label {
        display: none;
    }
    
    .inline-label-container {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 15px;
    }
    .inline-label-container > label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #D81B60;
        white-space: nowrap;
    }
    .inline-label-container > div {
        flex-grow: 1;
    }

    .warmup-box {
        background-color: #fff0f5;
        border-left: 5px solid #D81B60;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 25px;
        color: #000;
        line-height: 1.4;
    }
    @media (prefers-color-scheme: dark) {
        .warmup-box {
            background-color: #2d1a22;
            color: #fff;
        }
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
    if val_w1 is not None:
        if st.session_state.get(w2_key) is None: st.session_state[w2_key] = val_w1
        if st.session_state.get(w3_key) is None: st.session_state[w3_key] = val_w1

# --- CONNECT & LOAD ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    movements_db = conn.read(spreadsheet=SHEET_URL, worksheet="Exercise_bank", ttl=0)
    history_df = conn.read(spreadsheet=SHEET_URL, worksheet="Logs", usecols=[0, 1, 2, 3], ttl=0)
    if history_df.empty: history_df = pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])
except Exception as e:
    st.error(f"Sheet Error: {e}")
    st.stop()

# --- UI HEADER ---
img_light = get_base64_image("Pippafit_Light.png")
img_dark = get_base64_image("Pippafit_Dark.png")
if img_light and img_dark:
    st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{img_light}" class="logo-light"><img src="data:image/png;base64,{img_dark}" class="logo-dark"></div>', unsafe_allow_html=True)

# --- DAY SELECTION ---
if 'selected_day' not in st.session_state:
    st.session_state.selected_day = datetime.now().strftime("%A") if datetime.now().strftime("%A") in ["Monday", "Wednesday", "Saturday"] else "Monday"

col_mon, col_wed, col_sat = st.columns(3)
if col_mon.button("Monday", type="primary" if st.session_state.selected_day == "Monday" else "secondary", use_container_width=True):
    st.session_state.selected_day = "Monday"
    st.rerun()
if col_wed.button("Wednesday", type="primary" if st.session_state.selected_day == "Wednesday" else "secondary", use_container_width=True):
    st.session_state.selected_day = "Wednesday"
    st.rerun()
if col_sat.button("Saturday", type= "primary" if st.session_state.selected_day == "Saturday" else "secondary", use_container_width=True):
    st.session_state.selected_day = "Saturday"
    st.rerun()

# --- WARM UP INSTRUCTION ---
st.markdown("""
<div class="warmup-box">
    <h3 style="margin-top:0; color:#D81B60;">🔥 Warm up</h3>
    🏃 <b>10 MINS</b> | Treadmill<br><br>
    <b>VISUALISE</b> the gift you give yourself at <b>65</b>.<br><br>
    Imagine the <b>OUTCOMES</b> of the effort you put in <b>NOW</b> when you blow out those candles, surrounded by <b>family who loves you.

So let's get to work!S
</b><br><br>
    </b>
</div>
""", unsafe_allow_html=True)

# --- THE MUSCLE GROUP SPREAD ---
day_data = movements_db[movements_db['Day'] == st.session_state.selected_day]

if day_data.empty:
    st.info(f"No workout scheduled for {st.session_state.selected_day}.")
else:
    muscle_groups = day_data['Target Group'].unique()
    
    for muscle in muscle_groups:
        with st.container(border=True):
            options = day_data[day_data['Target Group'] == muscle]
            ex_list = options['Exercise'].tolist()
            
            sb_key = f"sb_{muscle}_{st.session_state.selected_day}"
            if sb_key not in st.session_state:
                st.session_state[sb_key] = ex_list[0]
            
            st.markdown(f'<p class="muscle-header">{muscle}</p>', unsafe_allow_html=True)
            st.markdown(f'<div class="exercise-title">{st.session_state[sb_key]}</div>', unsafe_allow_html=True)
            
            # INLINE SELECTOR
            st.markdown('<div class="inline-label-container"><label>Swap exercise (optional)</label>', unsafe_allow_html=True)
            selected_ex = st.selectbox("Swap exercise (optional)", ex_list, key=sb_key, label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
            
            raw_video = options[options['Exercise'] == selected_ex].iloc[0]['Video Link']
            if pd.notna(raw_video) and str(raw_video).strip():
                clean_video = format_youtube_url(str(raw_video).strip())
                with st.expander("▶️ Exercise tutorial"):
                    st.video(clean_video)

            ex_history = history_df[history_df['Exercise'] == selected_ex].copy()
            target_msg = "No history"
            if not ex_history.empty:
                ex_history['Date'] = pd.to_datetime(ex_history['Date'], errors='coerce')
                last_session_date = ex_history.sort_values(by='Date').iloc[-1]['Date'].date()
                last_session = ex_history[ex_history['Date'].dt.date == last_session_date]
                if not last_session.empty:
                    best = last_session.sort_values(by=['Weight', 'Reps']).iloc[-1]
                    target_msg = f"Target: {float(best['Weight'])}kg x {int(best['Reps'])}"

            tab_log, tab_edit = st.tabs(["Log Sets", "Edit"])

            with tab_log:
                st.caption(f"**{target_msg}**")
                k1, k2, k3 = f"{selected_ex}_w1", f"{selected_ex}_w2", f"{selected_ex}_w3"
                r1, r2, r3 = f"{selected_ex}_r1", f"{selected_ex}_r2", f"{selected_ex}_r3"

                for i, (kw, kr) in enumerate([(k1, r1), (k2, r2), (k3, r3)], 1):
                    c_w, c_r = st.columns(2)
                    c_w.number_input(f"Set {i} Kg", value=None, step=1.25, key=kw, on_change=update_weights if i==1 else None, args=(selected_ex,) if i==1 else None)
                    c_r.number_input(f"Set {i} Reps", value=None, step=1, key=kr)

                if st.button("SAVE SETS", type="primary", key=f"save_{selected_ex}_{muscle}", use_container_width=True):
                    new_rows = []
                    for kw, kr in [(k1, r1), (k2, r2), (k3, r3)]:
                        val_r = st.session_state.get(kr)
                        if val_r:
                            new_rows.append({
                                "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                "Exercise": selected_ex, 
                                "Weight": st.session_state.get(kw) or 0, 
                                "Reps": val_r
                            })
                    if new_rows:
                        conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=pd.concat([history_df, pd.DataFrame(new_rows)], ignore_index=True))
                        st.toast(f"{selected_ex} logged!", icon="✅")
                        st.rerun()

            with tab_edit:
                recent = history_df[history_df['Exercise'] == selected_ex].sort_values(by='Date', ascending=False).head(3)
                if recent.empty: st.info("No logs.")
                else:
                    for idx, row in recent.iterrows():
                        st.caption(f"{pd.to_datetime(row['Date']).strftime('%d %b')}")
                        ec1, ec2, ec3 = st.columns([2, 2, 1])
                        nw = ec1.number_input("W", value=float(row['Weight']), key=f"editw_{idx}")
                        nr = ec2.number_input("R", value=int(row['Reps']), key=f"editr_{idx}")
                        if ec3.button("❌", key=f"del_{idx}"):
                            conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=history_df.drop(idx))
                            st.rerun()

    st.divider()
    if st.button("Complete workout", type="primary", use_container_width=True):
        st.balloons()
        st.success("Workout logged!")