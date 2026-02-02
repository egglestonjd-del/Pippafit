import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import base64
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIG ---
st.set_page_config(page_title="Pippafit 65", page_icon="💪")
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- EMAIL FUNCTION ---
def send_workout_email(summary_html):
    try:
        # Load secrets
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]
        receiver_email = st.secrets["email"]["receiver_email"]

        # Create Message
        msg = MIMEMultipart()
        msg['From'] = "Pippafit App <" + sender_email + ">"
        msg['To'] = receiver_email
        msg['Subject'] = f"💪 Workout Complete: {datetime.now().strftime('%A, %d %b')}"

        # Attach HTML body
        msg.attach(MIMEText(summary_html, 'html'))

        # Send
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email Error: {e}")
        return False

# --- CACHED DATA LOADING ---
@st.cache_data(ttl=600)
def get_movements_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(spreadsheet=SHEET_URL, worksheet="Exercise_bank")

@st.cache_data(ttl=10)
def get_logs_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=SHEET_URL, worksheet="Logs", usecols=[0, 1, 2, 3])
    if df.empty:
        return pd.DataFrame(columns=['Date', 'Exercise', 'Weight', 'Reps'])
    return df

# --- HELPERS ---
def format_youtube_url(url):
    if not isinstance(url, str): return url
    if "/shorts/" in url: return url.replace("/shorts/", "/watch?v=")
    return url

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError: return None

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

    div.stButton > button[kind="secondary"] {
        border: 1px solid #d0d0d0 !important;
    }

    /* Small Swap Trigger Styling */
    .swap-trigger-wrapper div.stButton > button {
        border: none !important;
        background-color: transparent !important;
        color: #D81B60 !important;
        text-decoration: underline !important;
        font-size: 0.8rem !important;
        padding: 0 !important;
        height: auto !important;
        min-height: unset !important;
        box-shadow: none !important;
        margin-bottom: 10px;
    }

    .stNumberInput input { font-weight: bold; }
    
    [data-baseweb="tab-list"] {
        width: 100%;
        display: flex;
    }
    button[data-baseweb="tab"]:nth-of-type(1) { width: 80% !important; }
    button[data-baseweb="tab"]:nth-of-type(2) { width: 20% !important; }

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
        line-height: 1.2;
        margin-bottom: 5px;
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
        .warmup-box { background-color: #2d1a22; color: #fff; }
    }

    .rest-text {
        color: #b0b0b0;
        font-size: 0.75rem;
        text-align: center;
        margin: 2px 0 10px 0;
    }

    .info-text {
        color: #888;
        font-size: 0.85rem;
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

# --- LOAD DATA ---
try:
    movements_db = get_movements_data()
    history_df = get_logs_data()
except Exception:
    st.error("Connection Error. Retrying...")
    st.stop()

# --- UI HEADER ---
img_light = get_base64_image("Pippafit_Light.png")
img_dark = get_base64_image("Pippafit_Dark.png")
if img_light and img_dark:
    st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{img_light}" class="logo-light"><img src="data:image/png;base64,{img_dark}" class="logo-dark"></div>', unsafe_allow_html=True)

# --- DAY SELECTION ---
days = ["Monday", "Wednesday", "Saturday"]
if 'selected_day' not in st.session_state:
    curr_day = datetime.now().strftime("%A")
    st.session_state.selected_day = curr_day if curr_day in days else "Monday"

cols = st.columns(3)
for i, day in enumerate(days):
    if cols[i].button(day, type="primary" if st.session_state.selected_day == day else "secondary", use_container_width=True):
        st.session_state.selected_day = day
        st.rerun()

# --- GLOBAL TREADMILL WARM UP ---
st.markdown("""
<div class="warmup-box">
    <h3 style="margin-top:0; color:#D81B60;">🔥 Warm up</h3>
    🏃 <b>10 MINS</b> | Treadmill<br><br>
    Visualise the gift you give yourself at <b>65</b>.<br>
    Focus on the outcomes of the effort you put in now.
</div>
""", unsafe_allow_html=True)

# --- WORKOUT SPREAD ---
day_data = movements_db[movements_db['Day'] == st.session_state.selected_day]

if day_data.empty:
    st.info(f"No workout scheduled for {st.session_state.selected_day}.")
else:
    for muscle in day_data['Target Group'].unique():
        with st.container(border=True):
            options = day_data[day_data['Target Group'] == muscle]
            ex_list = options['Exercise'].tolist()
            
            anchor_key = f"anchor_{muscle}_{st.session_state.selected_day}"
            if anchor_key not in st.session_state:
                st.session_state[anchor_key] = ex_list[0]
            
            st.markdown(f'<p class="muscle-header">{muscle}</p>', unsafe_allow_html=True)
            st.markdown(f'<div class="exercise-title">{st.session_state[anchor_key]}</div>', unsafe_allow_html=True)
            
            # --- SWAP INTERACTION ---
            swap_state_key = f"is_swapping_{muscle}"
            if swap_state_key not in st.session_state:
                st.session_state[swap_state_key] = False
            
            st.markdown('<div class="swap-trigger-wrapper">', unsafe_allow_html=True)
            if not st.session_state[swap_state_key]:
                if st.button("Swap exercise", key=f"btn_swap_{muscle}"):
                    st.session_state[swap_state_key] = True
                    st.rerun()
            else:
                selected_ex = st.selectbox(
                    "Choose alternative:", 
                    ex_list, 
                    index=ex_list.index(st.session_state[anchor_key]),
                    key=f"sb_{muscle}_{st.session_state.selected_day}"
                )
                if selected_ex != st.session_state[anchor_key]:
                    st.session_state[anchor_key] = selected_ex
                    st.session_state[swap_state_key] = False
                    st.rerun()
                if st.button("Cancel swap", key=f"cancel_{muscle}"):
                    st.session_state[swap_state_key] = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            current_exercise = st.session_state[anchor_key]
            
            # Watch demo
            video = options[options['Exercise'] == current_exercise].iloc[0]['Video Link']
            if pd.notna(video) and str(video).strip():
                with st.expander("▶️ Watch demo"):
                    st.video(format_youtube_url(str(video).strip()))

            # Info expander
            with st.expander("ⓘ info"):
                st.markdown("""
                <div class="info-text">
                <strong>Working Weight Selection</strong><br>
                • Choose a resistance you can move for 5–18 reps only.<br>
                • If you exceed 18 reps, increase weight.<br>
                • If you fail before 5 reps, reduce weight.<br>
                • Final reps should be difficult but controlled, with good form.<br><br>
                <strong>Warm-Up Protocol</strong><br>
                • Begin at 50% of your estimated max.<br>
                • Perform 6–10 controlled, easy reps.<br>
                • Increase weight to 90% of working weight.<br>
                • Test the new weight for a few reps.<br>
                • It should feel challenging but maintainable within the target rep range.
                </div>
                """, unsafe_allow_html=True)

            ex_history = history_df[history_df['Exercise'] == current_exercise].copy()
            target_msg = "No history"
            if not ex_history.empty:
                ex_history['Date'] = pd.to_datetime(ex_history['Date'], errors='coerce')
                last_date = ex_history.sort_values(by='Date').iloc[-1]['Date'].date()
                last_session = ex_history[ex_history['Date'].dt.date == last_date]
                if not last_session.empty:
                    best = last_session.sort_values(by=['Weight', 'Reps']).iloc[-1]
                    target_msg = f"Target: {float(best['Weight'])}kg x {int(best['Reps'])}"

            # Chart
            chart_data = history_df[history_df['Exercise'] == current_exercise][['Date', 'Weight']].copy()
            if not chart_data.empty:
                st.line_chart(chart_data, x='Date', y='Weight', height=150)

            tab_log, tab_edit = st.tabs(["Log Sets", "Edit"])

            with tab_log:
                st.caption(f"**{target_msg}**")
                for i in range(1, 4):
                    with st.container(border=True):
                        st.markdown(f"###### Set {i}")
                        kw, kr = f"{current_exercise}_w{i}", f"{current_exercise}_r{i}"
                        
                        c_w, c_r = st.columns(2)
                        
                        # Added max_value and help text
                        c_w.number_input(
                            "Kg", 
                            value=None, 
                            step=1.25, 
                            key=kw, 
                            max_value=150.0, 
                            help="Maximum weight is 150kg. Please reduce input if higher.",
                            on_change=update_weights if i==1 else None, 
                            args=(current_exercise,) if i==1 else None
                        )
                        
                        c_r.number_input(
                            "Reps", 
                            value=None, 
                            step=1, 
                            key=kr, 
                            max_value=25,
                            help="Maximum reps is 25. Please reduce input if higher."
                        )
                    
                    if i < 3:
                        st.markdown('<p class="rest-text">Rest 1 min between sets</p>', unsafe_allow_html=True)

                if st.button("SAVE SETS", type="primary", key=f"save_{current_exercise}_{muscle}", use_container_width=True):
                    new_rows = []
                    for i in range(1, 4):
                        r = st.session_state.get(f"{current_exercise}_r{i}")
                        if r:
                            new_rows.append({
                                "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                "Exercise": current_exercise, 
                                "Weight": st.session_state.get(f"{current_exercise}_w{i}") or 0, 
                                "Reps": r
                            })
                    if new_rows:
                        with st.spinner("Syncing..."):
                            conn = st.connection("gsheets", type=GSheetsConnection)
                            conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=pd.concat([history_df, pd.DataFrame(new_rows)], ignore_index=True))
                            st.cache_data.clear()
                        st.toast(f"{current_exercise} logged!", icon="✅")
                        st.rerun()

            with tab_edit:
                recent = history_df[history_df['Exercise'] == current_exercise].sort_values(by='Date', ascending=False).head(3)
                if recent.empty: st.info("No logs.")
                else:
                    for idx, row in recent.iterrows():
                        st.caption(f"{pd.to_datetime(row['Date']).strftime('%d %b')}")
                        ec1, ec2, ec3 = st.columns([2, 2, 1])
                        nw = ec1.number_input("W", value=float(row['Weight']), key=f"editw_{idx}")
                        nr = ec2.number_input("R", value=int(row['Reps']), key=f"editr_{idx}")
                        if ec3.button("❌", key=f"del_{idx}"):
                            conn = st.connection("gsheets", type=GSheetsConnection)
                            conn.update(spreadsheet=SHEET_URL, worksheet="Logs", data=history_df.drop(idx))
                            st.cache_data.clear()
                            st.rerun()

    st.divider()
    if st.button("Complete workout", type="primary", use_container_width=True):
        # 1. Fetch Fresh Data (bypass cache to get the very latest logs)
        conn = st.connection("gsheets", type=GSheetsConnection)
        fresh_history = conn.read(spreadsheet=SHEET_URL, worksheet="Logs", usecols=[0, 1, 2, 3])
        
        # 2. Filter for Today
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_logs = fresh_history[fresh_history['Date'].str.contains(today_str, na=False)]
        
        if not today_logs.empty:
            # 3. Create HTML Table for Email
            html_table = """
            <table style="border-collapse: collapse; width: 100%; border: 1px solid #ddd; font-family: Arial, sans-serif;">
                <tr style="background-color: #D81B60; color: white;">
                    <th style="padding: 10px; border: 1px solid #ddd;">Exercise</th>
                    <th style="padding: 10px; border: 1px solid #ddd;">Weight (kg)</th>
                    <th style="padding: 10px; border: 1px solid #ddd;">Reps</th>
                </tr>
            """
            for _, row in today_logs.iterrows():
                html_table += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{row['Exercise']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{row['Weight']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{row['Reps']}</td>
                </tr>
                """
            html_table += "</table>"
            
            with st.spinner("Sending summary email..."):
                if send_workout_email(html_table):
                    st.balloons()
                    st.success("Great job! Workout summary sent.")
                else:
                    st.warning("Workout saved, but email failed. Check secrets config.")
        else:
            st.info("No logs found for today yet.")