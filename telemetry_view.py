import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_telemetry_comparison(session, driver1, driver2, lap_number):
    """
    Compares telemetry inputs (Throttle, Brake, RPM, Speed) between two drivers.
    """
    try:
        laps1 = session.laps.pick_driver(driver1)
        laps2 = session.laps.pick_driver(driver2)
        
        # Select the specific lap
        lap1 = laps1[laps1['LapNumber'] == lap_number].iloc[0]
        lap2 = laps2[laps2['LapNumber'] == lap_number].iloc[0]
        
        # Get telemetry data
        tel1 = lap1.get_car_data().add_distance()
        tel2 = lap2.get_car_data().add_distance()
        
        # Create Subplots
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                            vertical_spacing=0.02,
                            subplot_titles=("Speed (km/h)", "Throttle (%)", "Brake (On/Off)", "RPM"))
        
        # Colors (f1-dash style: Speed=White, Throttle=Green, Brake=Red, RPM=Blue)
        colors = {driver1: '#FFFFFF', driver2: '#FF1801'} 
        
        for driver, tel, c in [(driver1, tel1, colors[driver1]), (driver2, tel2, colors[driver2])]:
            # Speed
            fig.add_trace(go.Scatter(x=tel['Distance'], y=tel['Speed'], name=f"{driver} Speed", 
                                   line=dict(color=c, width=2)), row=1, col=1)
            # Throttle
            fig.add_trace(go.Scatter(x=tel['Distance'], y=tel['Throttle'], name=f"{driver} Throttle",
                                   line=dict(color=c, width=1.5, dash='solid')), row=2, col=1)
            # Brake
            fig.add_trace(go.Scatter(x=tel['Distance'], y=tel['Brake'], name=f"{driver} Brake",
                                   fill='tozeroy' if driver==driver1 else None,
                                   line=dict(color=c, width=1)), row=3, col=1)
            # RPM
            fig.add_trace(go.Scatter(x=tel['Distance'], y=tel['RPM'], name=f"{driver} RPM",
                                   line=dict(color=c, width=1)), row=4, col=1)

        fig.update_layout(
            template="plotly_dark",
            height=800,
            hovermode="x unified",
            margin=dict(l=50, r=20, t=50, b=50),
            title_text=f"Telemetry Deep Dive: {driver1} vs {driver2} (Lap {lap_number})"
        )
        
        # Styling y-axes limits based on f1-dash constraints
        fig.update_yaxes(title_text="km/h", row=1, col=1)
        fig.update_yaxes(title_text="%", range=[0, 105], row=2, col=1)
        fig.update_yaxes(title_text="On/Off", range=[-0.1, 1.1], row=3, col=1)
        fig.update_yaxes(title_text="RPM", row=4, col=1)
        fig.update_xaxes(title_text="Distance (m)", row=4, col=1)
        
        return fig
    except Exception as e:
        print(f"Telemetry Error: {e}")
        return None
