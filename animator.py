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
        Mimics f1-dash's Map component with corner numbers and smooth dots.
        """
        if not self.session:
            return None

        # 1. Get Lap Window
        try:
            # Sync to the winner's lap timing, or first available
            try:
                # Robustly find the winner or leader
                if 'Position' in self.session.results.columns:
                    winner = self.session.results.loc[self.session.results['Position'] == 1.0, 'Abbreviation'].iloc[0]
                else:
                    winner = self.session.results.iloc[0]['Abbreviation']
            except:
                # Fallback to the first driver in the list if results aren't standard
                winner = self.session.drivers[0]
            
            laps = self.session.laps.pick_driver(winner)
            if laps.empty: 
                print(f"No laps data for driver {winner}")
                return None

            try:
                ref_lap = laps.pick_lap(lap_number)
            except:
                print(f"Could not pick lap {lap_number} for {winner}")
                return None

            if hasattr(ref_lap, 'empty') and ref_lap.empty: 
                print(f"Lap {lap_number} is empty for {winner}")
                return None
            
            t_start, t_end = ref_lap['LapStartTime'], ref_lap['Time']
            
            # --- FIX: Handle Missing Start Time (Common on Lap 1) ---
            if pd.isnull(t_start):
                # Attempt to infer start time from LapTime
                if not pd.isnull(ref_lap['LapTime']):
                    t_start = t_end - ref_lap['LapTime']
                elif lap_number == 1:
                    # If Lap 1 and no LapTime, assume start of session data or 0
                    # Try to find the minimum time in telemetry for this driver
                    try:
                        drv_tel = laps.get_telemetry()
                        t_start = drv_tel['Time'].min()
                    except:
                        t_start = pd.Timedelta(seconds=0)
            
            if pd.isnull(t_start) or pd.isnull(t_end):
                print(f"Invalid timing for Lap {lap_number}: Start={t_start}, End={t_end}")
                return None

            # Resample time for animation (lower resolution for performance)
            # 500ms intervals = 2fps roughly, good for web
            common_time = pd.timedelta_range(start=t_start, end=t_end, freq='500ms')
        except Exception as e:
            print(f"Animation Window Error: {e}")
            return None

        # 2. Get Track Map (Fastest Lap Telemetry)
        try:
            fastest_lap = self.session.laps.pick_fastest()
            # If pick_fastest fails or returns empty (e.g. no valid laps set yet), pick the best available
            if hasattr(fastest_lap, 'empty') and fastest_lap.empty:
                fastest_lap = laps.pick_fastest()
                if hasattr(fastest_lap, 'empty') and fastest_lap.empty:
                     # Last resort: just pick the reference lap
                     fastest_lap = ref_lap
            
            circuit = fastest_lap.get_telemetry()
        except Exception as e:
             print(f"Track Map Error: {e}")
             return None
        
        # 3. Get Corner Data (if available via circuit_info, otherwise approximation)
        corners = pd.DataFrame()
        if hasattr(self.session, 'circuit_info'):
            corners = self.session.circuit_info.corners
        
        # 4. Prepare Driver Data
        try:
            # Get top 10 drivers safely
            if 'Position' in self.session.results.columns:
                 top_drivers = self.session.results.sort_values('Position').iloc[:10]['Abbreviation'].tolist()
            else:
                 top_drivers = self.session.results.iloc[:10]['Abbreviation'].tolist()
        except:
            top_drivers = self.session.drivers[:10]
        
        driver_positions = {}
        for driver in top_drivers:
            try:
                d_laps = self.session.laps.pick_driver(driver)
                # Get telemetry for the specific time window
                # Note: get_telemetry() on laps object joins all laps. 
                # We need to slice it by time.
                tel = d_laps.get_telemetry()
                
                # Filter by the time window of the leader's lap
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
                # ffill/bfill to handle edge cases at start/end of interpolation
                window[['X', 'Y']] = window[['X', 'Y']].ffill().bfill()
                
                driver_positions[driver] = window.loc[common_time][['X', 'Y']]
            except:
                continue

        if not driver_positions:
            print("No driver position data available.")
            return None

        # 5. Build Frames
        frames = []
        for i, t in enumerate(common_time):
            frame_data = []
            for driver in top_drivers:
                if driver in driver_positions:
                    try:
                        pos = driver_positions[driver].iloc[i]
                        # Check for NaN in position
                        if pd.isna(pos['X']) or pd.isna(pos['Y']): continue
                        
                        frame_data.append(
                            go.Scatter(
                                x=[pos['X']], y=[pos['Y']],
                                mode='markers+text',
                                marker=dict(size=12, color=self._get_driver_color(driver), line=dict(width=1, color='white')),
                                text=[driver], textposition="top center",
                                name=driver
                            )
                        )
                    except: continue
            frames.append(go.Frame(data=frame_data, name=str(i)))

        # 6. Create Figure
        # Initial positions (t=0 of the window)
        initial_traces = []
        for d in top_drivers:
            if d in driver_positions:
                try:
                    pos0 = driver_positions[d].iloc[0]
                    if pd.isna(pos0['X']): continue
                    initial_traces.append(
                        go.Scatter(
                            x=[pos0['X']], y=[pos0['Y']],
                            mode='markers+text',
                            marker=dict(size=12, color=self._get_driver_color(d)),
                            text=[d],
                            name=d
                        )
                    )
                except: continue

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
            ] + initial_traces,
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

        # Add Corners (Static)
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
        # Helper to find color (simplified)
        try:
            # Check if 'TeamName' column exists, otherwise handle gracefully
            if 'TeamName' not in self.session.results.columns:
                return "#FFFFFF"
                
            # Filter for the driver
            driver_res = self.session.results[self.session.results['Abbreviation'] == driver_abbr]
            if driver_res.empty: return "#FFFFFF"
            
            team = driver_res.iloc[0]['TeamName']
            
            # Fuzzy match team name to visualizer map
            for key, color in self.team_colors.items():
                if key.lower() in str(team).lower(): return color
            return "#FFFFFF"
        except:
            return "#FFFFFF"
