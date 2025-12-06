import streamlit as st
import pandas as pd
import fastf1
import plotly.express as px
import os

# --- IMPORT LOCAL MODULES ---
import data_collector
import visualizer
import dashboard

# 1. APP CONFIGURATION
st.set_page_config(
    page_title="F1 Analytics Pro",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. MODERN F1 UI STYLING
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@300;400;600;700&display=swap');
    
    .stApp { background-color: #0e0e0e; color: #e0e0e0; }
    html, body, [class*="css"] { font-family: 'Titillium Web', sans-serif; }
    h1, h2, h3 {
        color: #FF1801 !important;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }
    .f1-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        backdrop-filter: blur(10px);
    }
    .f1-card-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #FF1801;
        margin-bottom: 12px;
        border-bottom: 1px solid #333;
        padding-bottom: 8px;
    }
    .live-badge {
        background-color: #FF1801;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


# 3. CACHE SETUP
@st.cache_resource
def setup_cache():
    cache_dir = 'f1_cache'
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    fastf1.Cache.enable_cache(cache_dir)


setup_cache()


# --- HELPER FUNCTIONS ---
def get_race_control_messages(session):
    try:
        rc = session.race_control_messages
        if rc is None or rc.empty:
            return pd.DataFrame()
        rc['Time'] = rc['Time'].dt.total_seconds().apply(
            lambda x: f"{int(x//3600):02}:{int((x%3600)//60):02}:{int(x%60):02}"
        )
        return rc.sort_values(by='Time', ascending=False)
    except Exception:
        return pd.DataFrame()


def get_leaderboard(session):
    try:
        results = session.results
        df = results[['Position', 'Abbreviation', 'TeamName', 'Status', 'Points']].copy()
        df['Position'] = df['Position'].astype(int)
        return df
    except Exception:
        return pd.DataFrame()


# 4. SIDEBAR NAVIGATION
with st.sidebar:
    st.title("F1 ANALYTICS")
    page = st.radio("MENU", ["Dashboard", "Live Telemetry", "Strategy Lab"])
    st.markdown("---")
    year = st.selectbox("Season", [2025, 2024, 2023], index=1)

    if 'last_year' not in st.session_state:
        st.session_state['last_year'] = year
    if st.session_state['last_year'] != year:
        st.session_state['data_loaded'] = False
        st.session_state['last_year'] = year

# --- PAGE 1: DASHBOARD ---
if page == "Dashboard":
    st.title(f"SEASON {year} OVERVIEW")
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Sync Season Data", use_container_width=True):
            with st.spinner("Syncing..."):
                try:
                    data_collector.collect_full_season_data(year)
                    st.rerun()
                except Exception as e:
                    st.warning(f"Sync partial/failed: {e}")

    try:
        df = visualizer.load_data(year)
        if df is not None:
            latest_round = int(df['Round'].max())
            leader = df.groupby('Driver')['Points'].sum().idxmax()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rounds", f"{latest_round}/24")
            c2.metric("Leader", leader)
            c3.metric("Top Team", df.groupby('Team')['Points'].sum().idxmax())
            c4.metric("Avg Speed", f"{df['Speed'].mean():.0f} km/h")

            st.markdown("### 🏆 Championship Battle")
            st.plotly_chart(visualizer.plot_championship_standings(df), use_container_width=True)

            st.markdown("### 🏎️ Constructor Performance")
            st.plotly_chart(visualizer.plot_team_performance(df), use_container_width=True)
        else:
            st.info("No data available. Please click 'Sync Season Data'.")
    except Exception as e:
        st.error(f"Dashboard Error: {e}")

# --- PAGE 2: LIVE TELEMETRY ---
elif page == "Live Telemetry":
    h1, h2 = st.columns([4, 1])
    with h1:
        st.title("RACE CONTROL CENTER")
    with h2:
        st.markdown(
            '<div style="text-align: right; margin-top: 15px;"><span class="live-badge">LIVE REPLAY</span></div>',
            unsafe_allow_html=True
        )

    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races_with_data = schedule[schedule['Session5'].notna()]
        race_map = dict(zip(races_with_data['EventName'], races_with_data['RoundNumber']))

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            selected_race = st.selectbox("Grand Prix", list(race_map.keys()), index=len(race_map)-1)
        with c2:
            session_type = st.selectbox("Session", ["Race", "Qualifying", "Sprint"], index=0)
        with c3:
            st.write("")
            load_btn = st.button("LOAD SESSION", type="primary", use_container_width=True)

        if load_btn or st.session_state.get('data_loaded'):
            st.session_state['data_loaded'] = True
            round_num = race_map[selected_race]
            s_type = 'R' if session_type == "Race" else ('Q' if session_type == "Qualifying" else 'S')

            with st.spinner(f"Connecting to {selected_race} telemetry..."):
                session = fastf1.get_session(year, round_num, s_type)
                session.load(telemetry=True, weather=True, messages=True)

                col_left, col_right = st.columns([1, 2])
                with col_left:
                    st.markdown('<div class="f1-card"><div class="f1-card-header">📊 LEADERBOARD</div>', unsafe_allow_html=True)
                    lb_df = get_leaderboard(session)
                    st.dataframe(
                        lb_df,
                        column_config={
                            "Abbreviation": "Driver",
                            "TeamName": "Team",
                            "Points": st.column_config.ProgressColumn(
                                "Pts", format="%d", min_value=0, max_value=26
                            )
                        },
                        hide_index=True,
                        use_container_width=True,
                        height=400
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

                with col_right:
                    st.markdown('<div class="f1-card"><div class="f1-card-header">🗺️ TRACK POSITION</div>', unsafe_allow_html=True)
                    try:
                        track_fig = px.line(
                            session.laps.pick_fastest().get_telemetry(),
                            x='X', y='Y', height=400
                        )
                        track_fig.update_traces(line_color='#FF1801', line_width=4)
                        track_fig.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(visible=False),
                            yaxis=dict(visible=False),
                            margin=dict(l=0, r=0, t=0, b=0)
                        )
                        st.plotly_chart(track_fig, use_container_width=True)
                    except Exception:
                        st.info("Map data unavailable")
                    st.markdown('</div>', unsafe_allow_html=True)

                c_rc, c_vio, c_weather = st.columns(3)
                all_msgs = get_race_control_messages(session)

                with c_rc:
                    st.markdown('<div class="f1-card"><div class="f1-card-header">📢 RACE CONTROL</div>', unsafe_allow_html=True)
                    if not all_msgs.empty:
                        rc_msgs = all_msgs[~all_msgs['Message'].str.contains("VIOLATION|PENALTY", case=False, na=False)]
                        st.dataframe(rc_msgs[['Time', 'Message']], hide_index=True, use_container_width=True, height=300)
                    else:
                        st.write("No messages.")
                    st.markdown('</div>', unsafe_allow_html=True)

                with c_vio:
                    st.markdown('<div class="f1-card"><div class="f1-card-header">⚠️ INCIDENTS</div>', unsafe_allow_html=True)
                    if not all_msgs.empty:
                        vio_msgs = all_msgs[all_msgs['Message'].str.contains("VIOLATION|PENALTY", case=False, na=False)]
                        if not vio_msgs.empty:
                            st.dataframe(vio_msgs[['Time', 'Message']], hide_index=True, use_container_width=True, height=300)
                        else:
                            st.success("Clean Race")
                    st.markdown('</div>', unsafe_allow_html=True)

                with c_weather:
                    st.markdown('<div class="f1-card"><div class="f1-card-header">🌤️ ATMOSPHERE</div>', unsafe_allow_html=True)
                    if not session.weather_data.empty:
                        curr_w = session.weather_data.iloc[-1]
                        c_a, c_b = st.columns(2)
                        c_a.metric("Air", f"{curr_w['AirTemp']}°C")
                        c_a.metric("Track", f"{curr_w['TrackTemp']}°C")
                        c_b.metric("Hum", f"{curr_w['Humidity']}%")
                        c_b.metric("Press", f"{curr_w['Pressure']}mb")
                    else:
                        st.write("Weather unavailable")
                    st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Race Center Error: {e}")

# --- PAGE 3: STRATEGY LAB ---
elif page == "Strategy Lab":
    st.title("♟️ STRATEGY & PACE ANALYSIS")
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        if not schedule.empty:
            races_with_data = schedule[schedule['Session5'].notna()]
            completed_races = races_with_data['EventName'].tolist()

            if completed_races:
                sel_race = st.selectbox("Select Race", completed_races)
                if st.button("Analyze Strategy"):
                    with st.spinner("Crunching numbers..."):
                        r_map = dict(zip(schedule['EventName'], schedule['RoundNumber']))
                        round_num = r_map[sel_race]
                        session = fastf1.get_session(year, round_num, 'R')
                        session.load()

                        st.markdown("### 🛞 Tyre Compound History")
                        fig = dashboard.plot_strategy_dashboard(year, round_num)
                        if fig:
                            st.pyplot(fig)

                        st.markdown("### ⏱️ Pace Distribution")
                        try:
                            laps = session.laps.pick_quicklaps()
                            fig_pace = px.box(
                                laps, x="Driver", y="LapTimeSeconds", color="Team",
                                title="Lap Time Distribution"
                            )
                            fig_pace.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
                            st.plotly_chart(fig_pace, use_container_width=True)
                        except Exception as e:
                            st.warning(f"Pace analysis failed: {e}")
            else:
                st.info("No races completed yet.")
        else:
            st.error("Could not fetch schedule.")
    except Exception as e:
        st.error(f"Strategy Error: {e}")
