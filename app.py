import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import fastf1
import os

# --- IMPORT LOCAL MODULES ---
# Ensure these files are in the same directory (root)
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

# 2. CUSTOM CSS STYLING (F1 Dark Theme & Fonts)
st.markdown("""
<style>
    /* Import Titillium Web Font (Official F1 style) */
    @import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Titillium Web', sans-serif;
    }
    
    /* Headers - F1 Red */
    h1, h2, h3 {
        color: #FF1801 !important; 
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* KPI Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        color: #FFFFFF !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        color: #AAAAAA !important;
    }
    
    /* Glassmorphism Card Style */
    .stCard {
        background-color: #151515;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #FF1801;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    
    /* Primary Action Buttons */
    div.stButton > button {
        background-color: #FF1801;
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 700;
        text-transform: uppercase;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #CC0000; /* Darker red on hover */
        transform: scale(1.02);
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E1E1E;
        border-radius: 4px;
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF1801 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. CACHE SETUP (Crucial for Cloud Performance)
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
    
    # Navigation Menu
    page = st.radio(
        "NAVIGATION", 
        ["Dashboard", "Deep Dive", "Live Replay"], 
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Season Selector
    year = st.selectbox("SEASON", [2025, 2024, 2023], index=0)
    
    st.markdown("---")
    st.caption(f"Status: Connected\nAPI Cache: Enabled")

# --- PAGE 1: CHAMPIONSHIP DASHBOARD ---
if page == "Dashboard":
    st.title(f"SEASON {year} OVERVIEW")
    
    # Header & Sync Button
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

    # Load & Visualize Data
    try:
        df = visualizer.load_data(year)
        
        if df is not None:
            # High-Level Metrics
            latest_round = int(df['Round'].max())
            leader = df.groupby('Driver')['Points'].sum().idxmax()
            top_team = df.groupby('Team')['Points'].sum().idxmax()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Rounds Complete", f"{latest_round}/24")
            m2.metric("Driver Leader", leader)
            m3.metric("Constructor Leader", top_team)
            
            st.markdown("---")
            
            # Interactive Plotly Charts
            tab1, tab2 = st.tabs(["📈 Driver Standings", "📊 Team Performance"])
            
            with tab1:
                st.markdown("### Championship Trajectory")
                fig_drivers = visualizer.plot_championship_standings(df)
                st.plotly_chart(fig_drivers, use_container_width=True)
                
            with tab2:
                st.markdown("### Constructor Points")
                fig_teams = visualizer.plot_team_performance(df)
                st.plotly_chart(fig_teams, use_container_width=True)
                
        else:
            st.info("⚠️ No local data found for this season.")
            st.markdown("Click the **'Sync Data'** button above to download the latest results.")
            
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")


# --- PAGE 2: STRATEGY DEEP DIVE ---
elif page == "Deep Dive":
    st.title("♟️ STRATEGY ANALYSIS")
    st.markdown("Analyze tyre compounds, stint lengths, and pit stop strategies.")
    
    try:
        # Fetch Race List
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races_with_data = schedule[schedule['Session5'].notna()]
        race_map = dict(zip(races_with_data['EventName'], races_with_data['RoundNumber']))
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Configuration")
            selected_race_name = st.selectbox(
                "Select Grand Prix", 
                list(race_map.keys()), 
                index=len(race_map)-1
            )
            
            if st.button("Analyze Strategy", type="primary", use_container_width=True):
                st.session_state['show_strategy'] = True
        
        with col2:
            if st.session_state.get('show_strategy'):
                round_num = race_map[selected_race_name]
                st.markdown(f"### Stint Analysis: {selected_race_name}")
                
                with st.spinner(f"Analyzing Tyre Data for Round {round_num}..."):
                    try:
                        # Renders Matplotlib chart from dashboard.py
                        fig = dashboard.plot_strategy_dashboard(year, round_num=round_num)
                        st.pyplot(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Analysis failed. Data might be incomplete. Error: {e}")
            else:
                st.info("👈 Select a race to view tyre strategies.")
                
    except Exception as e:
        st.error(f"Could not load race schedule: {e}")


# --- PAGE 3: TELEMETRY REPLAY (HTML ANIMATION) ---
elif page == "Live Replay":
    st.title("🎞️ RACE REPLAY")
    st.caption("Visualizing position changes for Lap 5 (Lightweight HTML Animation)")
    
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races_with_data = schedule[schedule['Session5'].notna()]
        race_map = dict(zip(races_with_data['EventName'], races_with_data['RoundNumber']))
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Replay Setup")
            selected_race_name = st.selectbox("Select Race", list(race_map.keys()), index=len(race_map)-1)
            
            if st.button("Generate Animation", type="primary", use_container_width=True):
                st.session_state['generate_anim'] = True
                
        with col2:
            if st.session_state.get('generate_anim'):
                round_num = race_map[selected_race_name]
                
                with st.spinner("Processing Telemetry & Rendering..."):
                    try:
                        # Calls animator.py (HTML version)
                        html_animation = animator.animate_race(year, round_num=round_num)
                        
                        # Error Check
                        if isinstance(html_animation, str) and "Error" in html_animation[:20]:
                             st.error(html_animation)
                        else:
                             st.success(f"Rendering Complete: {selected_race_name}")
                             # Render the HTML directly (No video file needed)
                             components.html(html_animation, height=700, scrolling=False)
                             
                    except Exception as e:
                        st.error(f"Animation failed: {e}")
            else:
                st.info("👈 Choose a race to start the replay engine.")

    except Exception as e:
        st.error(f"Could not load race list: {e}")
