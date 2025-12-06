import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import numpy as np

# Enable FastF1 built-in plotting configurations
# misc_mpl_mods=False prevents FastF1 from messing with some tick labels which we want to control
fastf1.plotting.setup_mpl(misc_mpl_mods=False)

class RaceAnimator:
    def __init__(self, year=2025, round_num=None):
        self.year = year
        self.round_num = round_num
        self.session = None
        
    def load_session(self):
        """Loads the race session and telemetry data."""
        try:
            # Load Race session with full telemetry
            self.session = fastf1.get_session(self.year, self.round_num, 'R')
            self.session.load(telemetry=True, laps=True)
            return True
        except Exception as e:
            print(f"Error loading session: {e}")
            return False

    def create_animation(self, lap_number=1):
        """
        Generates a robust HTML animation.
        Uses SESSION TIME to sync drivers, creating a 'Live Replay' effect.
        """
        if not self.session:
            return "Session not loaded."

        # 1. Identify the Time Window based on the Leader
        # We want to view the race during the time the leader was on 'lap_number'
        try:
            # Get the driver who won or led this lap
            top_driver = self.session.results.iloc[0]['Abbreviation']
            leader_laps = self.session.laps.pick_driver(top_driver)
            
            # Select the specific lap
            specific_lap = leader_laps[leader_laps['LapNumber'] == lap_number].iloc[0]
            
            # Define Start and End Session Times
            t_start = specific_lap['LapStartTime']
            t_end = specific_lap['Time'] # End of lap
            
            # Create the master clock (ticks every 200ms)
            # This ensures all drivers are synced to the exact same moments
            common_time = pd.timedelta_range(start=t_start, end=t_end, freq='200ms')
            
        except IndexError:
            return f"<h3>Data Error</h3><p>Could not find timing data for Lap {lap_number}. It might not have happened yet.</p>"
        except Exception as e:
            return f"<h3>Error</h3><p>{str(e)}</p>"

        # 2. Collect Data for Top 10 Drivers
        # We fetch their location during the EXACT SAME window defined above
        top_drivers = self.session.results['Abbreviation'].iloc[:10].tolist()
        driver_data = {}
        
        # Track limits for axis scaling
        all_x = []
        all_y = []

        for driver in top_drivers:
            try:
                # Get all telemetry for the driver
                # We fetch the whole session telemetry first to ensure we cover the window
                # (Efficient enough for 10 drivers)
                d_laps = self.session.laps.pick_driver(driver)
                tel = d_laps.get_telemetry()
                
                # Filter for our specific time window
                # We use a buffer of 1 second to ensure interpolation works at the edges
                mask = (tel['Time'] >= t_start - pd.Timedelta('1s')) & (tel['Time'] <= t_end + pd.Timedelta('1s'))
                window_tel = tel.loc[mask].copy()
                
                if window_tel.empty:
                    continue

                # RE-INDEXING & INTERPOLATION (The secret to smooth animation)
                # 1. Set index to Time
                window_tel = window_tel.set_index('Time')
                
                # 2. Merge our common_time index into the data
                # This adds rows for our specific tick marks (NaN values initially)
                combined_index = window_tel.index.union(common_time).sort_values()
                window_tel = window_tel.reindex(combined_index)
                
                # 3. Interpolate strictly numeric columns (X, Y, Speed)
                # 'time' method respects the actual time gap between points
                window_tel['X'] = window_tel['X'].interpolate(method='time')
                window_tel['Y'] = window_tel['Y'].interpolate(method='time')
                window_tel['Speed'] = window_tel['Speed'].interpolate(method='time')
                window_tel['nGear'] = window_tel['nGear'].ffill() # Forward fill gear (discrete)
                
                # 4. Extract only the exact ticks we need
                final_data = window_tel.loc[common_time]
                
                # Store valid data
                driver_data[driver] = {
                    'color': fastf1.plotting.get_driver_color(driver, session=self.session),
                    'x': final_data['X'].to_numpy(),
                    'y': final_data['Y'].to_numpy(),
                    'speed': final_data['Speed'].fillna(0).to_numpy(),
                    'gear': final_data['nGear'].fillna(1).to_numpy()
                }
                
                # Collect coordinates for auto-scaling
                all_x.extend(final_data['X'].dropna().tolist())
                all_y.extend(final_data['Y'].dropna().tolist())

            except Exception as e:
                print(f"Skipping {driver}: {e}")
                continue

        if not driver_data:
            return "<h3>No Telemetry Found</h3><p>Could not process drivers for this lap.</p>"

        # 3. Setup Plot
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # CRITICAL FIX: Set explicit axis limits so the track doesn't disappear
        # We add a 200m buffer around the min/max coordinates
        if all_x and all_y:
            buffer = 200
            ax.set_xlim(min(all_x) - buffer, max(all_x) + buffer)
            ax.set_ylim(min(all_y) - buffer, max(all_y) + buffer)
        else:
            ax.axis('equal') # Fallback
            
        ax.axis('off')
        fig.patch.set_facecolor('#0E1117') # Match Streamlit Dark Theme
        ax.set_facecolor('#0E1117')

        # Draw Static Track Map (Background)
        # We use the fastest lap of the session for the cleanest track shape
        try:
            fastest_lap = self.session.laps.pick_fastest()
            fl_tel = fastest_lap.get_telemetry()
            ax.plot(fl_tel['X'], fl_tel['Y'], color='#222222', linewidth=8, zorder=1) # Tarmac
            ax.plot(fl_tel['X'], fl_tel['Y'], color='#333333', linewidth=3, zorder=2) # Centerline
        except:
            pass # If fastest lap fails, we just don't draw the background track

        # 4. Initialize Animation Objects
        cars = {}
        labels = {}
        
        # Info Text
        title_text = ax.text(0.02, 0.95, f"LAP {lap_number} REPLAY", transform=ax.transAxes, 
                           color='white', fontsize=12, fontweight='bold', zorder=10)
        
        leader_text = ax.text(0.02, 0.90, "Waiting for data...", transform=ax.transAxes,
                            color='#FF1801', fontsize=10, fontfamily='monospace', zorder=10)

        # Create Line2D objects for each driver
        for driver, data in driver_data.items():
            dot, = ax.plot([], [], 'o', color=data['color'], markersize=8, 
                           markeredgecolor='white', markeredgewidth=1, zorder=5)
            txt = ax.text(0, 0, driver, color='white', fontsize=7, fontweight='bold', zorder=6)
            cars[driver] = dot
            labels[driver] = txt

        # 5. Update Function
        def update(frame):
            artists = [title_text, leader_text]
            
            # Update Leader Stats (First in list)
            leader_name = top_drivers[0]
            if leader_name in driver_data:
                s = driver_data[leader_name]['speed'][frame]
                g = driver_data[leader_name]['gear'][frame]
                leader_text.set_text(f"LDR: {leader_name} | {int(s)} km/h | G{int(g)}")

            # Update Positions
            for driver, dot in cars.items():
                d = driver_data[driver]
                if frame < len(d['x']):
                    x, y = d['x'][frame], d['y'][frame]
                    
                    # Update dot
                    dot.set_data([x], [y])
                    
                    # Update label (slight offset)
                    labels[driver].set_position((x + 80, y + 80))
                    
                    artists.append(dot)
                    artists.append(labels[driver])
            
            return artists

        # 6. Render
        # blit=True creates smooth animation but requires returning changed artists
        ani = animation.FuncAnimation(
            fig, update, frames=len(common_time), blit=True, interval=100
        )
        
        plt.close(fig)
        return ani.to_jshtml()
