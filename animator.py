import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import numpy as np

# Setup Dark Mode for Matplotlib
plt.style.use('dark_background')

def animate_race(year=2025, round_num=None, save_path="race_animation.mp4"):
    if round_num is None: raise ValueError("Round Number missing.")
    
    # Load Data
    try:
        session = fastf1.get_session(year, round_num, 'R')
        session.load()
    except Exception as e:
        return f"Error: {e}"

    # Setup Drivers (Top 8 for cleaner visual)
    drivers = session.results['Abbreviation'].iloc[:8].tolist()
    target_lap = 5
    
    # Create Time Index (5fps for smooth but small video)
    try:
        leader = drivers[0]
        laps = session.laps.pick_drivers(leader).pick_laps(target_lap).iloc[0]
        common_time = pd.timedelta_range(start=laps['LapStartTime'], end=laps['Time'], freq='200ms')
    except:
        return "Error: Data unavailable for this lap."

    # Batch Process Data
    driver_data = []
    for d in drivers:
        try:
            lap = session.laps.pick_drivers(d).pick_laps(target_lap).iloc[0]
            tel = lap.get_telemetry()
            merged = pd.merge_asof(pd.DataFrame({'Time': common_time}), tel[['Time','X','Y']], on='Time', direction='nearest')
            driver_data.append({
                'id': d,
                'color': fastf1.plotting.get_driver_color(d, session=session),
                'x': merged['X'].to_numpy(),
                'y': merged['Y'].to_numpy()
            })
        except: continue

    # VISUAL SETUP
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.axis('off') # Remove box
    ax.set_facecolor('black')
    fig.patch.set_facecolor('black')
    
    # Static Track Map (Grey line)
    ref = driver_data[0]
    ax.plot(ref['x'], ref['y'], color='#333333', linewidth=12, zorder=1) # Thick track border
    ax.plot(ref['x'], ref['y'], color='#111111', linewidth=8, zorder=2)  # Inner asphalt

    # Dynamic Elements
    scatters = []
    texts = []
    trails = [] # List to store trail lines
    
    for d in driver_data:
        # Trail (The line behind the car)
        trail, = ax.plot([], [], color=d['color'], alpha=0.6, linewidth=2, zorder=3)
        trails.append(trail)
        
        # Car Dot (Neon glow effect using edge color)
        dot, = ax.plot([], [], 'o', color=d['color'], markersize=10, 
                       markeredgecolor='white', markeredgewidth=1.5, zorder=5)
        scatters.append(dot)
        
        # Driver Label
        txt = ax.text(0, 0, d['id'], color='white', fontsize=9, fontweight='bold', zorder=6)
        texts.append(txt)

    # Title
    ax.text(0.05, 0.95, f"LAP {target_lap} REPLAY", transform=ax.transAxes, 
            color='white', fontsize=16, fontweight='bold', fontfamily='monospace')

    def update(frame):
        for i, d in enumerate(driver_data):
            if frame < len(d['x']):
                x, y = d['x'][frame], d['y'][frame]
                
                # Update Dot
                scatters[i].set_data([x], [y])
                
                # Update Label
                texts[i].set_position((x + 80, y + 80))
                
                # Update Trail (Show last 15 positions)
                start_idx = max(0, frame - 15)
                trails[i].set_data(d['x'][start_idx:frame], d['y'][start_idx:frame])
                
        return scatters + texts + trails

    # Render MP4
    ani = animation.FuncAnimation(fig, update, frames=len(common_time), blit=True)
    writer = animation.FFMpegWriter(fps=20, bitrate=2500)
    ani.save(save_path, writer=writer)
    plt.close()
    
    return save_path