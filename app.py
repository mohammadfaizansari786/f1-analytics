import streamlit as st
import pandas as pd
import fastf1
import plotly.express as px
import plotly.graph_objects as go
import os

# --- IMPORT LOCAL MODULES ---
import data_collector
import visualizer
import dashboard
import telemetry_view
from animator import RaceAnimator

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

    /* Custom Card Style */
    .f1-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        backdrop-filter: blur(10px);
        transition: transform 0.2s;
    }
    .f1-card:hover {
        transform: translateY(-2px);
        border-color: #FF1801;
    }

    .f1-card-header {
        font-size: 1.2rem;
        font-weight: 700;
        color: #FF1801;
        margin-bottom: 15px;
        border-bottom: 1px solid #333;
        padding-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .live-badge {
        background-color: #FF1801;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 24, 1, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 24, 1, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 24, 1, 0); }
    }

    /* Stats Metric Styling */
    div[data-testid="stMetricValue"] {
        color: #FFFFFF;
        font-family: 'Titillium Web', sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #222;
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
@st.cache_resource
def get_session_data(year, race, session_type):
    """Robust session loader"""
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        round_num = schedule.loc[schedule['EventName'] == race, 'RoundNumber'].iloc[0]
        session = fastf1.get_session(year, round_num, session_type)
        session.load(telemetry=True, weather=True, messages=True)
        return session, round_num
    except Exception as e:
        return None, str(e)

# 4. SIDEBAR NAVIGATION
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/3/33/F1.svg", width=100) # Placeholder logo
    st.title("F1 ANALYTICS PRO")

    page = st.radio(
        "NAVIGATION",
        ["Dashboard", "Live Telemetry & Animation", "Driver Analytics", "Car Performance", "Strategy Lab"],
        index=0
    )

    st.markdown("---")
    year = st.selectbox("Season", [2025, 2024, 2023], index=1)

    # State management for race selection persistence
    if 'last_year' not in st.session_state:
        st.session_state['last_year'] = year
    if st.session_state['last_year'] != year:
        st.session_state['data_loaded'] = False
        st.session_state['last_year'] = year

# ==========================================
# PAGE 1: SEASON DASHBOARD
# ==========================================
if page == "Dashboard":
    st.title(f"SEASON {year} OVERVIEW")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Sync Season Data", use_container_width=True):
            with st.spinner("Fetching latest season data..."):
                try:
                    data_collector.collect_full_season_data(year)
                    st.rerun()
                except Exception as e:
                    st.error(f"Sync failed: {e}")

    df = visualizer.load_data(year)
    if df is not None and not df.empty:
        latest_round = int(df['Round'].max())

        # Summary Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rounds Completed", f"{latest_round}")

        try:
            leader = df.groupby('Driver')['Points'].sum().idxmax()
            top_team = df.groupby('Team')['Points'].sum().idxmax()

            m2.metric("Driver Leader", leader)
            m3.metric("Constructor Leader", top_team)
            m4.metric("Avg Points/Round", f"{df['Points'].mean():.1f}")
        except:
            pass

        # Visualizations
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="f1-card">', unsafe_allow_html=True)
            st.plotly_chart(visualizer.plot_championship_standings(df), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="f1-card">', unsafe_allow_html=True)
            st.plotly_chart(visualizer.plot_team_performance(df), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info(f"No data available for {year}. Click 'Sync Season Data' to initialize.")

# ==========================================
# PAGE 2: LIVE TELEMETRY & ANIMATION
# ==========================================
elif page == "Live Telemetry & Animation":
    h1, h2 = st.columns([3, 1])
    with h1:
        st.title("RACE CONTROL & ANIMATION")
    with h2:
         st.markdown(
            '<div style="text-align: right; margin-top: 15px;"><span class="live-badge">LIVE REPLAY</span></div>',
            unsafe_allow_html=True
        )

    # Race Selection
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    races_with_data = schedule[schedule['Session5'].notna()]['EventName'].tolist()

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        selected_race = st.selectbox("Select Grand Prix", races_with_data, index=len(races_with_data)-1 if races_with_data else 0)
    with c2:
        session_type = st.selectbox("Session", ["Race", "Qualifying"], index=0)
    with c3:
        st.write("")
        load_btn = st.button("LOAD SESSION", type="primary", use_container_width=True)

    if load_btn or st.session_state.get('telemetry_loaded'):
        st.session_state['telemetry_loaded'] = True

        # Load Session Data
        s_type = 'R' if session_type == "Race" else 'Q'
        with st.spinner(f"Loading {selected_race} telemetry..."):
            session, round_num = get_session_data(year, selected_race, s_type)

        if session:
            # 1. Animation Section
            st.markdown("### 🏎️ Live Race Animation")
            st.markdown("Replay the race lap by lap. Select a lap number to visualize positions.")

            lap_slider = st.slider("Select Lap", 1, int(session.laps['LapNumber'].max()), 1)

            if st.button("Generate Animation Frame"):
                animator = RaceAnimator(year, round_num)
                # Manually inject already loaded session to save time
                animator.session = session

                with st.spinner("Rendering animation..."):
                    fig_anim = animator.create_plotly_animation(lap_number=lap_slider)
                    if fig_anim:
                        st.plotly_chart(fig_anim, use_container_width=True)
                    else:
                        st.warning("Could not generate animation for this lap.")

            # 2. Telemetry Overview
            st.markdown("---")
            col_left, col_right = st.columns([1, 2])

            with col_left:
                st.markdown('<div class="f1-card"><div class="f1-card-header">📊 LEADERBOARD</div>', unsafe_allow_html=True)
                try:
                    lb_df = session.results[['Position', 'Abbreviation', 'TeamName', 'Points']].copy()
                    lb_df['Position'] = lb_df['Position'].astype(int)
                    st.dataframe(lb_df, hide_index=True, use_container_width=True, height=400)
                except:
                    st.write("Leaderboard unavailable")
                st.markdown('</div>', unsafe_allow_html=True)

            with col_right:
                st.markdown('<div class="f1-card"><div class="f1-card-header">🗺️ TRACK MAP</div>', unsafe_allow_html=True)
                try:
                    lap = session.laps.pick_fastest()
                    if not lap.empty:
                        tel = lap.get_telemetry()
                        track_fig = px.line(tel, x='X', y='Y', title=f"Fastest Lap: {lap['Driver']}")
                        track_fig.update_traces(line_color='#FF1801', line_width=4)
                        track_fig.update_layout(
                            template="plotly_dark",
                            xaxis=dict(visible=False), yaxis=dict(visible=False),
                            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
                        )
                        st.plotly_chart(track_fig, use_container_width=True)
                except Exception as e:
                    st.info(f"Map data unavailable: {e}")
                st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# PAGE 3: DRIVER ANALYTICS
# ==========================================
elif page == "Driver Analytics":
    st.title("🧑‍🚀 DRIVER PERFORMANCE")

    # Use last loaded session if possible, else prompt
    # For simplicity, let's ask to select race again or assume last one
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    races = schedule[schedule['Session5'].notna()]['EventName'].tolist()

    sel_race = st.selectbox("Select Race for Analysis", races, index=len(races)-1 if races else 0)

    if st.button("Load Driver Data"):
        with st.spinner("Analyzing driver metrics..."):
            session, _ = get_session_data(year, sel_race, 'R')

            if session:
                st.markdown("### ⏱️ Lap Time Evolution")
                lap_fig = telemetry_view.plot_lap_times(session)
                if lap_fig:
                    st.plotly_chart(lap_fig, use_container_width=True)

                st.markdown("### ⚔️ Head-to-Head Telemetry")
                d1, d2 = st.columns(2)
                drivers = sorted(session.results['Abbreviation'].unique())

                with d1:
                    drv_a = st.selectbox("Driver A", drivers, index=0)
                with d2:
                    drv_b = st.selectbox("Driver B", drivers, index=1 if len(drivers)>1 else 0)

                lap_num = st.number_input("Lap Number", min_value=1, max_value=int(session.laps['LapNumber'].max()), value=1)

                tel_fig, err = telemetry_view.plot_telemetry_comparison(session, drv_a, drv_b, lap_num)
                if tel_fig:
                    st.plotly_chart(tel_fig, use_container_width=True, height=800)
                elif err:
                    st.error(err)

# ==========================================
# PAGE 4: CAR PERFORMANCE
# ==========================================
elif page == "Car Performance":
    st.title("🏎️ CAR TECHNICAL ANALYSIS")
    st.info("Select a race to compare top speeds and cornering performance.")

    schedule = fastf1.get_event_schedule(year, include_testing=False)
    races = schedule[schedule['Session5'].notna()]['EventName'].tolist()
    sel_race = st.selectbox("Select Race", races, key="car_race")

    if st.button("Analyze Cars"):
        with st.spinner("Processing telemetry..."):
            session, _ = get_session_data(year, sel_race, 'Q') # Quali is better for max performance
            if session:
                st.markdown("### 🚀 Speed Trap Comparison")
                # Simple bar chart of max speeds
                try:
                    max_speeds = []
                    for drv in session.results['Abbreviation']:
                        laps = session.laps.pick_driver(drv)
                        if not laps.empty:
                            fastest = laps.pick_fastest()
                            if not fastest.empty: # Check if fastest lap exists
                                # Avoid get_car_data() if possible for speed, use SpeedST if available or telemetry
                                try:
                                    tel = fastest.get_car_data()
                                    max_speed = tel['Speed'].max()
                                    max_speeds.append({'Driver': drv, 'Team': session.results.loc[session.results['Abbreviation']==drv, 'TeamName'].iloc[0], 'MaxSpeed': max_speed})
                                except:
                                    pass

                    if max_speeds:
                        df_speed = pd.DataFrame(max_speeds).sort_values('MaxSpeed', ascending=False)
                        fig_speed = px.bar(df_speed, x='Driver', y='MaxSpeed', color='Team',
                                         title="Maximum Speed by Driver (Qualifying)",
                                         template="plotly_dark",
                                         color_discrete_map=visualizer.get_team_color_map())
                        st.plotly_chart(fig_speed, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not calculate max speeds: {e}")

# ==========================================
# PAGE 5: STRATEGY LAB
# ==========================================
elif page == "Strategy Lab":
    st.title("♟️ STRATEGY & TYRE HISTORY")

    schedule = fastf1.get_event_schedule(year, include_testing=False)
    races = schedule[schedule['Session5'].notna()]['EventName'].tolist()
    sel_race = st.selectbox("Select Race", races, key="strat_race")

    if st.button("Show Strategy"):
        with st.spinner("Loading strategy data..."):
             # We use the existing logic but improved
             round_num = schedule.loc[schedule['EventName'] == sel_race, 'RoundNumber'].iloc[0]

             # Capture matplotlib figure
             st.markdown("### 🛞 Tyre Usage History")
             try:
                 # Redirect stdout to suppress terminal spam
                 fig = dashboard.plot_strategy_dashboard(year, round_num)
                 if fig:
                     st.pyplot(fig)
                 else:
                     st.warning("No strategy data available.")
             except Exception as e:
                 st.error(f"Strategy Error: {e}")
