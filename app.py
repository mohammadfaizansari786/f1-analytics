import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import fastf1
import os

# --- IMPORT LOCAL MODULES ---
import data_collector
import visualizer
import animator
import dashboard
import telemetry_view

# 1. APP CONFIGURATION
st.set_page_config(
    page_title="F1 2025 Command Center", 
    page_icon="🏎️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CUSTOM CSS STYLING
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Titillium Web', sans-serif;
    }
    
    h1, h2, h3 {
        color: #FF1801 !important; 
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Metrics Box */
    div[data-testid="stMetricValue"] {
        font-family: 'Titillium Web', monospace;
        font-size: 24px;
        color: white;
    }
    
    /* Custom Card */
    .weather-card {
        background-color: #1c1c1c;
        border-radius: 8px;
        padding: 15px;
        border-top: 3px solid #FF1801;
        text-align: center;
    }
    
    /* Live Tag */
    .live-tag {
        background-color: #FF1801;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
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

# 4. SIDEBAR NAVIGATION
with st.sidebar:
    st.title("🏁 F1 INSIGHTS")
    st.markdown("_Advanced Telemetry & Analytics_")
    
    st.markdown("---")
    
    page = st.radio(
        "NAVIGATION", 
        ["Dashboard", "Race Center", "Strategy & Pace"], 
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    year = st.selectbox("SEASON", [2025, 2024, 2023], index=0)
    
    # Session State Reset on Year Change
    if 'last_year' not in st.session_state:
        st.session_state['last_year'] = year
    if st.session_state['last_year'] != year:
        st.session_state['data_loaded'] = False
        st.session_state['last_year'] = year

# --- PAGE 1: DASHBOARD ---
if page == "Dashboard":
    st.title(f"SEASON {year} OVERVIEW")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Sync Data", use_container_width=True):
            with st.spinner("Updating database..."):
                try:
                    data_collector.collect_full_season_data(year)
                    st.success("Updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")

    try:
        df = visualizer.load_data(year)
        if df is not None:
            latest_round = int(df['Round'].max())
            leader = df.groupby('Driver')['Points'].sum().idxmax()
            top_team = df.groupby('Team')['Points'].sum().idxmax()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Rounds Complete", f"{latest_round}/24")
            m2.metric("Driver Leader", leader)
            m3.metric("Constructor Leader", top_team)
            
            st.markdown("---")
            tab1, tab2 = st.tabs(["📈 Driver Standings", "📊 Team Performance"])
            with tab1:
                st.plotly_chart(visualizer.plot_championship_standings(df), use_container_width=True)
            with tab2:
                st.plotly_chart(visualizer.plot_team_performance(df), use_container_width=True)
        else:
            st.info("⚠️ No local data found. Click 'Sync Data' to start.")
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")

# --- PAGE 2: RACE CENTER (Enhanced) ---
elif page == "Race Center":
    c_head, c_live = st.columns([5,1])
    with c_head:
        st.title("🔴 LIVE MATCH CENTER")
    with c_live:
        st.markdown('<div style="text-align: right; margin-top: 20px;"><span class="live-tag">LIVE FEED</span></div>', unsafe_allow_html=True)

    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races_with_data = schedule[schedule['Session5'].notna()]
        race_map = dict(zip(races_with_data['EventName'], races_with_data['RoundNumber']))
        
        # Selection Area
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            selected_race_name = st.selectbox("Select Grand Prix", list(race_map.keys()), index=len(race_map)-1)
        with c2:
            lap_select = st.number_input("Select Lap", min_value=1, max_value=70, value=1)
        with c3:
            st.write("") 
            load_btn = st.button("Initialize Data", type="primary", use_container_width=True)
        
        round_num = race_map[selected_race_name]
        anim = animator.RaceAnimator(year, round_num)
        
        # --- DATA LOADER ---
        if load_btn or st.session_state.get('data_loaded'):
            st.session_state['data_loaded'] = True
            
            with st.spinner("Fetching Session Data..."):
                if anim.load_session():
                    # --- WEATHER COMPONENT ---
                    # Only show if session has weather data
                    if hasattr(anim.session, 'weather_data'):
                        w = anim.session.weather_data.iloc[0] # Start of session weather
                        w_cols = st.columns(4)
                        with w_cols[0]: st.metric("Air Temp", f"{w['AirTemp']}°C")
                        with w_cols[1]: st.metric("Track Temp", f"{w['TrackTemp']}°C")
                        with w_cols[2]: st.metric("Humidity", f"{w['Humidity']}%")
                        with w_cols[3]: st.metric("Rain", "YES" if w['Rainfall'] else "NO")
                    
                    st.divider()

                    # --- TABS ---
                    tab_map, tab_tel = st.tabs(["🗺️ Ghost Map", "📈 Telemetry"])
                    
                    with tab_map:
                        fig = anim.create_plotly_animation(lap_number=lap_select)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(f"Map data unavailable for Lap {lap_select}.")

                    with tab_tel:
                        st.markdown("### Driver Input Comparison")
                        drivers = anim.session.results['Abbreviation'].tolist()
                        
                        dc1, dc2, dc3 = st.columns([1, 1, 1])
                        with dc1: d1 = st.selectbox("Driver 1", drivers, index=0)
                        with dc2: d2 = st.selectbox("Driver 2", drivers, index=1)
                        with dc3: 
                            st.write("")
                            compare_btn = st.button("Compare Inputs", use_container_width=True)
                        
                        if compare_btn:
                            with st.spinner("Processing..."):
                                t_fig, err = telemetry_view.plot_telemetry_comparison(anim.session, d1, d2, lap_select)
                                if t_fig:
                                    st.plotly_chart(t_fig, use_container_width=True)
                                else:
                                    st.error(f"Telemetry Error: {err}")
                else:
                    st.error("Failed to load session from FastF1.")

    except Exception as e:
        st.error(f"System Error: {e}")

# --- PAGE 3: STRATEGY & PACE ---
elif page == "Strategy & Pace":
    st.title("♟️ STRATEGY ANALYSIS")
    
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races_with_data = schedule[schedule['Session5'].notna()]
        race_map = dict(zip(races_with_data['EventName'], races_with_data['RoundNumber']))
        
        c1, c2 = st.columns([2, 1])
        with c1:
            selected_race = st.selectbox("Select Grand Prix", list(race_map.keys()), index=len(race_map)-1)
        with c2:
            st.write("")
            load_strat_btn = st.button("Load Analysis", type="primary", use_container_width=True)

        if load_strat_btn:
            round_num = race_map[selected_race]
            with st.spinner(f"Analyzing {selected_race}..."):
                # Load session locally for this page
                session = fastf1.get_session(year, round_num, 'R')
                session.load()
                
                t1, t2 = st.tabs(["🏎️ Race Pace", "🛞 Tyre Strategy"])
                
                with t1:
                    pace_fig = telemetry_view.plot_lap_times(session)
                    if pace_fig:
                        st.plotly_chart(pace_fig, use_container_width=True)
                    else:
                        st.warning("Could not load lap time data.")
                
                with t2:
                    # Fallback to matplotlib dashboard if needed, or implement plotly version
                    try:
                        fig = dashboard.plot_strategy_dashboard(year, round_num=round_num)
                        st.pyplot(fig, use_container_width=True)
                    except:
                        st.warning("Strategy data unavailable.")

    except Exception as e:
        st.error(f"Strategy Error: {e}")
