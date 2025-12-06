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
import telemetry_view  # Ensure this file exists in your directory

# 1. APP CONFIGURATION
st.set_page_config(
    page_title="F1 2025 Analytics Hub", 
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
    
    .stCard {
        background-color: #151515;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #FF1801;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 20px;
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
        ["Dashboard", "Deep Dive", "Live Match"], 
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    year = st.selectbox("SEASON", [2025, 2024, 2023], index=0)
    st.caption(f"Status: Connected\nAPI Cache: Enabled")

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

# --- PAGE 2: STRATEGY ---
elif page == "Deep Dive":
    st.title("♟️ STRATEGY ANALYSIS")
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races_with_data = schedule[schedule['Session5'].notna()]
        race_map = dict(zip(races_with_data['EventName'], races_with_data['RoundNumber']))
        
        col1, col2 = st.columns([1, 2])
        with col1:
            selected_race = st.selectbox("Select Grand Prix", list(race_map.keys()), index=len(race_map)-1)
            if st.button("Analyze Strategy", type="primary", use_container_width=True):
                st.session_state['show_strategy'] = True
        
        with col2:
            if st.session_state.get('show_strategy'):
                round_num = race_map[selected_race]
                with st.spinner(f"Analyzing {selected_race}..."):
                    try:
                        fig = dashboard.plot_strategy_dashboard(year, round_num=round_num)
                        st.pyplot(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
    except Exception as e:
        st.error(f"Could not load schedule: {e}")

# --- PAGE 3: LIVE MATCH (Enhanced) ---
elif page == "Live Match":
    col_header, col_badge = st.columns([5, 1])
    with col_header:
        st.title("🔴 LIVE MATCH CENTER")
    with col_badge:
        st.markdown('<div style="text-align: right; margin-top: 20px;"><span class="live-tag">LIVE FEED</span></div>', unsafe_allow_html=True)

    st.markdown("Interactive race replay and telemetry analysis.")

    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races_with_data = schedule[schedule['Session5'].notna()]
        race_map = dict(zip(races_with_data['EventName'], races_with_data['RoundNumber']))
        
        # Selection Area
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            selected_race_name = st.selectbox("Select Grand Prix", list(race_map.keys()), index=len(race_map)-1)
        with c2:
            # Allow user to select up to reasonable max laps, we can handle error later if it exceeds
            lap_select = st.number_input("Select Lap", min_value=1, max_value=70, value=1)
        with c3:
            st.write("") # Formatting spacer
            load_btn = st.button("Initialize Data", type="primary", use_container_width=True)
        
        round_num = race_map[selected_race_name]
        
        # TABS FOR VIEW
        tab_map, tab_tel = st.tabs(["🗺️ Track Map", "📈 Telemetry"])
        
        # Initialize Animator
        # Note: We create the object but only load heavy data when requested
        anim = animator.RaceAnimator(year, round_num)
        
        # --- TAB 1: INTERACTIVE MAP ---
        with tab_map:
            if load_btn or st.session_state.get('data_loaded'):
                st.session_state['data_loaded'] = True # Keep state active
                
                with st.spinner("Processing telemetry for replay..."):
                    if anim.load_session():
                        # Use the new Plotly animation method
                        fig = anim.create_plotly_animation(lap_number=lap_select)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                            st.caption(f"Showing Ghost Replay for Lap {lap_select}. Press Play to animate.")
                        else:
                            st.warning("No telemetry data available for this lap/driver combination.")
                    else:
                        st.error("Failed to load session data.")

        # --- TAB 2: TELEMETRY DEEP DIVE ---
        with tab_tel:
            st.markdown("### Driver Input Comparison")
            st.info("Compare throttle, brake, and speed traces between two drivers to analyze driving styles.")
            
            # We need the session loaded to get the driver list
            if st.session_state.get('data_loaded') and anim.session:
                drivers = anim.session.results['Abbreviation'].tolist()
                
                dc1, dc2, dc3 = st.columns([1, 1, 1])
                with dc1:
                    d1 = st.selectbox("Driver 1", drivers, index=0)
                with dc2:
                    d2 = st.selectbox("Driver 2", drivers, index=1)
                with dc3:
                    st.write("") # Spacer
                    compare_btn = st.button("Compare Inputs", use_container_width=True)
                
                if compare_btn:
                    with st.spinner(f"Comparing {d1} vs {d2}..."):
                        t_fig = telemetry_view.plot_telemetry_comparison(anim.session, d1, d2, lap_select)
                        if t_fig:
                            st.plotly_chart(t_fig, use_container_width=True)
                        else:
                            st.warning("Telemetry unavailable for one or both drivers on this lap.")
            else:
                st.caption("Please click 'Initialize Data' above to load the drivers list.")

    except Exception as e:
        st.error(f"System Error: {e}")
