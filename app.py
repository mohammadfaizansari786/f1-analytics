import streamlit as st
import pandas as pd
import fastf1
import os

# --- IMPORT MODULES ---
import data_collector
import visualizer
import animator
import dashboard
import telemetry_view  # NEW MODULE

# ... [Keep existing Config & CSS] ...

# --- PAGE 3: LIVE MATCH (Enhanced) ---
elif page == "Live Match":
    st.title("🔴 LIVE MATCH CENTER")
    st.markdown("Interactive race replay and telemetry analysis.")

    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races_with_data = schedule[schedule['Session5'].notna()]
        race_map = dict(zip(races_with_data['EventName'], races_with_data['RoundNumber']))
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            selected_race_name = st.selectbox("Select Grand Prix", list(race_map.keys()), index=len(race_map)-1)
        with c2:
            # Dynamic max lap
            lap_select = st.number_input("Select Lap", min_value=1, max_value=70, value=1)
        
        round_num = race_map[selected_race_name]
        
        # TABS FOR VIEW
        tab_map, tab_tel = st.tabs(["🗺️ Track Map", "📈 Telemetry"])
        
        # Initialize Animator
        anim = animator.RaceAnimator(year, round_num)
        
        with tab_map:
            if st.button("Load Replay", type="primary"):
                with st.spinner("Processing telemetry..."):
                    if anim.load_session():
                        fig = anim.create_plotly_animation(lap_number=lap_select)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.error("No data available for this lap.")
                    else:
                        st.error("Failed to load session.")

        with tab_tel:
            st.markdown("### Driver Input Comparison")
            if anim.load_session():
                drivers = anim.session.results['Abbreviation'].tolist()
                dc1, dc2 = st.columns(2)
                with dc1:
                    d1 = st.selectbox("Driver 1", drivers, index=0)
                with dc2:
                    d2 = st.selectbox("Driver 2", drivers, index=1)
                
                if st.button("Compare Inputs"):
                    t_fig = telemetry_view.plot_telemetry_comparison(anim.session, d1, d2, lap_select)
                    if t_fig:
                        st.plotly_chart(t_fig, use_container_width=True)
                    else:
                        st.warning("Telemetry unavailable.")

    except Exception as e:
        st.error(f"System Error: {e}")
