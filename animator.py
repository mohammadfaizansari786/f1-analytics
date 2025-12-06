import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import numpy as np
from matplotlib import font_manager

# Enable FastF1 built-in plotting configurations
fastf1.plotting.setup_mpl(misc_mpl_mods=False)

class RaceAnimator:
    def __init__(self, year=2025, round_num=None):
        self.year = year
        self.round_num = round_num
        self.session = None
        self.drivers = []
        
    def load_session(self):
        """Loads the race session and telemetry data."""
        try:
            self.session = fastf1.get_session(self.year, self.round_num, 'R')
            self.session.load()
            return True
        except Exception as e:
            print(f"Error loading session: {e}")
            return False

    def create_animation(self, lap_number=1):
        """Generates a high-quality HTML animation for a specific lap."""
        if not self.session:
            return "Session not loaded."

        # 1. Select Drivers (Top 10 for performance/clarity)
        top_drivers = self.session.results['Abbreviation'].iloc[:10].tolist()
        
        # 2. Get Reference Data (The Track)
        # We use the fastest lap of the session to draw the clean track line
        ref_lap = self.session.laps.pick_fastest()
        ref_tel = ref_lap.get_telemetry()
        
        # 3. Prepare Driver Data
        driver_data = {}
        
        # Create a common timeline for this specific lap
        # We find the leader's start and end time for this lap to define the window
        leader_lap = self.session.laps.pick_drivers(top_drivers[0]).pick_laps(lap_number).iloc[0]
        start_time = leader_lap['LapStartTime']
        end_time = leader_lap['Time']
        
        # Create a time range for 1 lap, interpolated to 200ms for smoothness (5fps)
        common_time = pd.timedelta_range(start=start_time, end=end_time, freq='200ms')
        
        for driver in top_drivers:
            try:
                # Get lap data for driver
                laps = self.session.laps.pick_drivers(driver).pick_laps(lap_number)
                if laps.empty: continue
                
                # Get telemetry
                lap = laps.iloc[0]
                tel = lap.get_telemetry()
                
                # Merge to common timeline
                merged = pd.merge_asof(
                    pd.DataFrame({'Time': common_time}),
                    tel[['Time', 'X', 'Y', 'Speed', 'nGear']],
                    on='Time',
                    direction='nearest'
                )
                
                driver_data[driver] = {
                    'color': fastf1.plotting.get_driver_color(driver, session=self.session),
                    'x': merged['X'].to_numpy(),
                    'y': merged['Y'].to_numpy(),
                    'speed': merged['Speed'].fillna(0).to_numpy(),
                    'gear': merged['nGear'].fillna(0).to_numpy()
                }
            except Exception as e:
                print(f"Skip driver {driver}: {e}")
                continue

        # 4. Setup Plot (Dark F1 Style)
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.axis('off')
        fig.patch.set_facecolor('#101010')
        ax.set_facecolor('#101010')
        
        # Draw Track Map (Static)
        ax.plot(ref_tel['X'], ref_tel['Y'], color='#2b2b2b', linewidth=12, zorder=1) # Border
        ax.plot(ref_tel['X'], ref_tel['Y'], color='#383838', linewidth=6, zorder=2)  # Tarmac

        # 5. Initialize Animatable Elements
        cars = {}
        labels = {}
        
        # Info Panel Text
        info_text = ax.text(0.02, 0.95, f"LAP {lap_number} | LIVE REPLAY", 
                           transform=ax.transAxes, color='white', fontsize=14, fontweight='bold')
        
        leader_speed_text = ax.text(0.02, 0.90, "", 
                                   transform=ax.transAxes, color='#FF1801', fontsize=12, fontfamily='monospace')

        for driver, data in driver_data.items():
            # Car Dot
            dot, = ax.plot([], [], 'o', color=data['color'], markersize=10, 
                           markeredgecolor='white', markeredgewidth=1.5, zorder=5)
            # Driver Label
            txt = ax.text(0, 0, driver, color='white', fontsize=9, fontweight='bold', zorder=6)
            
            cars[driver] = dot
            labels[driver] = txt

        # 6. Animation Loop
        def update(frame):
            artists = [info_text, leader_speed_text]
            
            # Update Leader Telemetry (First driver in list)
            leader_name = top_drivers[0]
            if leader_name in driver_data and frame < len(driver_data[leader_name]['speed']):
                s = driver_data[leader_name]['speed'][frame]
                g = driver_data[leader_name]['gear'][frame]
                leader_speed_text.set_text(f"{leader_name}: {int(s)} km/h [G{int(g)}]")

            # Update Cars
            for driver, dot in cars.items():
                d = driver_data[driver]
                if frame < len(d['x']):
                    x, y = d['x'][frame], d['y'][frame]
                    dot.set_data([x], [y])
                    
                    # Update Label Position (offset slightly)
                    txt = labels[driver]
                    txt.set_position((x + 100, y + 100))
                    
                    artists.append(dot)
                    artists.append(txt)
            
            return artists

        # Create Animation
        ani = animation.FuncAnimation(
            fig, update, frames=len(common_time), blit=True, interval=100
        )
        
        plt.close(fig)
        return ani.to_jshtml()
