import fastf1
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from visualizer import get_team_color_map

class RaceAnimator:
    def __init__(self, year=2025, round_num=None):
        self.year = year
        self.round_num = round_num
        self.session = None
        self.team_colors = get_team_color_map()

    def load_session(self):
        """Loads session with telemetry and circuit info."""
        try:
            self.session = fastf1.get_session(self.year, self.round_num, 'R')
            self.session.load(telemetry=True, laps=True)
            return True
        except Exception as e:
            print(f"Error loading session: {e}")
            return False

    def create_plotly_animation(self, lap_number=1):
        """
        Generates an interactive Plotly animation for a specific lap.
        """
        if not self.session:
            return None

        # 1. Get Lap Window
        try:
            # Sync to the winner's lap timing, or first available
            try:
                winner = self.session.results.iloc[0]['Abbreviation']
            except:
                winner = self.session.drivers[0]
            
            laps = self.session.laps.pick_driver(winner)
            if laps.empty: return None

            ref_lap = laps.pick_lap(lap_number)
            if hasattr(ref_lap, 'empty') and ref_lap.empty: return None
            
            t_start, t_end = ref_lap['LapStartTime'], ref_lap['Time']
            
            # Resample time for animation (500ms intervals)
            common_time = pd.timedelta_range(start=t_start, end=t_end, freq='500ms')
        except Exception as e:
            print(f"Animation init error: {e}")
            return None

        # 2. Get Track Map (Fastest Lap Telemetry)
        try:
            fastest_lap = self.session.laps.pick_fastest()
            circuit = fastest_lap.get_telemetry()
        except:
            return None
        
        # 3. Get Corner Data
        corners = pd.DataFrame()
        if hasattr(self.session, 'circuit_info'):
            corners = self.session.circuit_info.corners
        
        # 4. Prepare Driver Data
        try:
            top_drivers = self.session.results.iloc[:10]['Abbreviation'].tolist()
        except:
            top_drivers = self.session.drivers[:10]
        
        driver_positions = {}
        for driver in top_drivers:
            try:
                laps = self.session.laps.pick_driver(driver)
                tel = laps.get_telemetry()
                mask = (tel['Time'] >= t_start) & (tel['Time'] <= t_end)
                window = tel.loc[mask].set_index('Time')
                
                if window.empty: continue

                # Reindex to common clock
                combined_idx = window.index.union(common_time).sort_values()
                window = window.reindex(combined_idx)
                
                # Interpolate X/Y
                window['X'] = window['X'].interpolate(method='time')
                window['Y'] = window['Y'].interpolate(method='time')
                
                # Extract exact frames
                driver_positions[driver] = window.loc[common_time][['X', 'Y']]
            except:
                continue

        # 5. Build Frames
        frames = []
        for i, t in enumerate(common_time):
            frame_data = []
            for driver in top_drivers:
                if driver in driver_positions:
                    try:
                        pos = driver_positions[driver].iloc[i]
                        frame_data.append(
                            go.Scatter(
                                x=[pos['X']], y=[pos['Y']],
                                mode='markers+text',
                                marker=dict(size=12, color=self._get_driver_color(driver), line=dict(width=1, color='white')),
                                text=[driver], textposition="top center",
                                name=driver
                            )
                        )
                    except IndexError:
                        continue
            frames.append(go.Frame(data=frame_data, name=str(i)))

        # 6. Create Figure
        fig = go.Figure(
            data=[
                # Static Track Layer
                go.Scatter(
                    x=circuit['X'], y=circuit['Y'],
                    mode='lines',
                    line=dict(color='#333333', width=15),
                    hoverinfo='skip',
                    showlegend=False
                ),
                go.Scatter(
                    x=circuit['X'], y=circuit['Y'],
                    mode='lines',
                    line=dict(color='#FFFFFF', width=2),
                    hoverinfo='skip',
                    showlegend=False
                )
            ] + [ # Initial Driver Positions
                go.Scatter(
                    x=[driver_positions[d].iloc[0]['X']], 
                    y=[driver_positions[d].iloc[0]['Y']],
                    mode='markers+text',
                    marker=dict(size=12, color=self._get_driver_color(d)),
                    text=[d], textposition="top center",
                    name=d
                ) for d in top_drivers if d in driver_positions
            ],
            layout=go.Layout(
                template="plotly_dark",
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=''),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title='', scaleanchor="x", scaleratio=1),
                margin=dict(l=0, r=0, t=30, b=0),
                height=600,
                updatemenus=[dict(
                    type="buttons",
                    buttons=[dict(label="▶️ Play",
                                method="animate",
                                args=[None, dict(frame=dict(duration=200, redraw=False), fromcurrent=True)])],
                    showactive=False,
                    y=0, x=0, xanchor="left", yanchor="bottom"
                )]
            ),
            frames=frames
        )

        if not corners.empty:
            fig.add_trace(go.Scatter(
                x=corners['X'], y=corners['Y'],
                mode='text',
                text=corners['Number'],
                textfont=dict(size=10, color="yellow"),
                showlegend=False
            ))

        return fig

    def _get_driver_color(self, driver_abbr):
        try:
            if 'TeamName' not in self.session.results.columns:
                return "#FFFFFF"
            
            # Filter safely
            mask = self.session.results['Abbreviation'] == driver_abbr
            if not mask.any():
                return "#FFFFFF"
                
            team = self.session.results.loc[mask, 'TeamName'].values[0]
            for key, color in self.team_colors.items():
                if key in str(team): return color
            return "#FFFFFF"
        except:
            return "#FFFFFF"
