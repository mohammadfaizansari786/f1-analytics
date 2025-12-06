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

# --- PAGE 3: LIVE MATCH (Redesigned) ---
elif page == "Live Match":
    col_header, col_badge = st.columns([5, 1])
    with col_header:
        st.title("🔴 LIVE MATCH CENTER")
    with col_badge:
        st.markdown('<div style="text-align: right; margin-top: 20px;"><span class="live-tag">LIVE FEED</span></div>', unsafe_allow_html=True)

    st.markdown("Visualize race dynamics with telemetry-synced track animation.")

    try:
        # Get Schedule
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races_with_data = schedule[schedule['Session5'].notna()]
        race_map = dict(zip(races_with_data['EventName'], races_with_data['RoundNumber']))
        
        # UI Layout
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            selected_race_name = st.selectbox("Select Grand Prix", list(race_map.keys()), index=len(race_map)-1)
        with c2:
            lap_select = st.number_input("Select Lap", min_value=1, max_value=70, value=1)
        with c3:
            st.write("") # Spacer
            start_btn = st.button("▶ Start Feed", type="primary", use_container_width=True)

        # Logic
        if start_btn:
            round_num = race_map[selected_race_name]
            st.session_state['live_race'] = selected_race_name
            
            with st.status("Initializing Live Feed...", expanded=True) as status:
                status.write("📡 Connecting to Telemetry Stream...")
                anim = animator.RaceAnimator(year, round_num)
                
                status.write("📥 Bufferring Session Data...")
                success = anim.load_session()
                
                if success:
                    status.write("🎨 Rendering 3D-mapped Track...")
                    html_anim = anim.create_animation(lap_number=lap_select)
                    status.update(label="Feed Ready!", state="complete", expanded=False)
                    
                    st.divider()
                    st.markdown(f"### {selected_race_name} - Lap {lap_select}")
                    components.html(html_anim, height=600, scrolling=False)
                else:
                    status.update(label="Connection Failed", state="error")
                    st.error("Could not load race data. The session might not be available yet.")

    except Exception as e:
        st.error(f"System Error: {e}")
