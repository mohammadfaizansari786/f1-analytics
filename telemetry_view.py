import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd  # <--- Added missing import

def plot_telemetry_comparison(session, driver1, driver2, lap_number):
    """
    Compares telemetry inputs (Speed, Throttle, Brake, Gear) between two drivers.
    """
    try:
        # 1. Robust Data Loading
        laps1 = session.laps.pick_driver(driver1)
        laps2 = session.laps.pick_driver(driver2)
        
        # Check if drivers exist
        if laps1.empty or laps2.empty:
            return None, f"One of the drivers ({driver1}, {driver2}) has no data."

        # Check if lap exists
        lap1_data = laps1[laps1['LapNumber'] == lap_number]
        lap2_data = laps2[laps2['LapNumber'] == lap_number]

        if lap1_data.empty:
            return None, f"{driver1} did not complete Lap {lap_number}."
        if lap2_data.empty:
            return None, f"{driver2} did not complete Lap {lap_number}."

        # Get Telemetry
        lap1 = lap1_data.iloc[0]
        lap2 = lap2_data.iloc[0]
        
        tel1 = lap1.get_car_data().add_distance()
        tel2 = lap2.get_car_data().add_distance()
        
        # 2. Create Subplots (Added Gear)
        fig = make_subplots(rows=5, cols=1, shared_xaxes=True,
                            vertical_spacing=0.03,
                            row_heights=[0.3, 0.15, 0.15, 0.2, 0.2],
                            subplot_titles=("Speed", "Throttle", "Brake", "RPM", "Gear"))
        
        colors = {driver1: '#FFFFFF', driver2: '#FF1801'} 

        # Determine Brake Range (Handle 0-1 vs 0-100 scales)
        max_brake = max(tel1['Brake'].max(), tel2['Brake'].max())
        brake_range = [-0.1, 1.1] if max_brake <= 1.1 else [0, 105]
        brake_title = "On/Off" if max_brake <= 1.1 else "%"
        
        for driver, tel, c in [(driver1, tel1, colors[driver1]), (driver2, tel2, colors[driver2])]:
            # Speed
            fig.add_trace(go.Scatter(x=tel['Distance'], y=tel['Speed'], name=f"{driver} Speed", 
                                   line=dict(color=c, width=2), legendgroup=driver), row=1, col=1)
            # Throttle
            fig.add_trace(go.Scatter(x=tel['Distance'], y=tel['Throttle'], name=f"{driver} Throttle",
                                   line=dict(color=c, width=1.5), showlegend=False), row=2, col=1)
            # Brake
            fig.add_trace(go.Scatter(x=tel['Distance'], y=tel['Brake'], name=f"{driver} Brake",
                                   fill='tozeroy' if driver==driver1 else None,
                                   line=dict(color=c, width=1), showlegend=False), row=3, col=1)
            # RPM
            fig.add_trace(go.Scatter(x=tel['Distance'], y=tel['RPM'], name=f"{driver} RPM",
                                   line=dict(color=c, width=1), showlegend=False), row=4, col=1)
            # Gear
            fig.add_trace(go.Scatter(x=tel['Distance'], y=tel['nGear'], name=f"{driver} Gear",
                                   line=dict(color=c, width=1.5, shape='hv'), showlegend=False), row=5, col=1)

        # 3. Styling
        fig.update_layout(
            template="plotly_dark",
            height=900,
            hovermode="x unified",
            margin=dict(l=50, r=20, t=60, b=50),
            title_text=f"Telemetry Battle: {driver1} vs {driver2} (Lap {lap_number})",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117"
        )
        
        fig.update_yaxes(title_text="km/h", row=1, col=1)
        fig.update_yaxes(title_text="%", range=[0, 105], row=2, col=1)
        fig.update_yaxes(title_text=brake_title, range=brake_range, row=3, col=1, showticklabels=(max_brake > 1.1))
        fig.update_yaxes(title_text="RPM", row=4, col=1)
        fig.update_yaxes(title_text="Gear", row=5, col=1)
        fig.update_xaxes(title_text="Distance (m)", row=5, col=1)
        
        return fig, None
    except Exception as e:
        return None, str(e)

def plot_lap_times(session):
    """New: Compares lap times for all drivers."""
    try:
        laps = session.laps
        try:
            drivers = session.results['Abbreviation'].unique()[:10] # Top 10
        except:
            drivers = session.drivers[:10]
        
        fig = go.Figure()
        
        for drv in drivers:
            drv_laps = laps.pick_driver(drv)
            if drv_laps.empty: continue
            
            # Filter out in/out laps (slow)
            drv_laps = drv_laps[drv_laps['LapTime'].notna()]
            if drv_laps.empty: continue

            # Quick anomaly filter (107% rule approx)
            min_lap = drv_laps['LapTime'].min()
            
            # FIX: pandas (pd) is now imported, so this line works
            if pd.isna(min_lap): continue
            
            threshold = min_lap * 1.07
            drv_laps = drv_laps[drv_laps['LapTime'] < threshold]
            
            fig.add_trace(go.Scatter(
                x=drv_laps['LapNumber'],
                y=drv_laps['LapTime'].dt.total_seconds(),
                mode='lines+markers',
                name=drv
            ))
            
        fig.update_layout(
            title="Race Pace Analysis (Top 10)",
            xaxis_title="Lap Number",
            yaxis_title="Lap Time (s)",
            template="plotly_dark",
            height=500,
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117"
        )
        return fig
    except Exception as e:
        print(f"Error plotting lap times: {e}")
        return None
