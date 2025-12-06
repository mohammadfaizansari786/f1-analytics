import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import numpy as np

# Setup Dark Mode
plt.style.use('dark_background')

def animate_race(year=2025, round_num=None):
    if round_num is None:
        raise ValueError("Round Number must be provided.")

    # 1. Load Data
    try:
        session = fastf1.get_session(year, round_num, 'R')
        session.load()
    except Exception as e:
        return f"Error loading session: {e}"
    
    # 2. Setup Drivers (Top 8 to keep size manageable)
    drivers_list = session.results['Abbreviation'].iloc[:8].tolist()
    target_lap = 5
    
    # 3. Smart Downsampling (The Fix for 'Size is too much')
    # freq='400ms' creates ~2.5 frames per second. 
    # This keeps the HTML string small enough to not crash the browser.
    try:
        leader = drivers_list[0]
        laps_leader = session.laps.pick_drivers(leader).pick_laps(target_lap).iloc[0]
        common_time = pd.timedelta_range(start=laps_leader['LapStartTime'], end=laps_leader['Time'], freq='400ms')
    except IndexError:
        return "Error: Could not find leader data for this lap."

    # 4. Batch Process Telemetry
    driver_data = []
    for driver in drivers_list:
        try:
            laps = session.laps.pick_drivers(driver).pick_laps(target_lap)
            if laps.empty: continue
            
            lap = laps.iloc[0]
            tel = lap.get_telemetry()
            
            # Synchronize to common timeline
            merged = pd.merge_asof(
                pd.DataFrame({'Time': common_time}), 
                tel[['Time', 'X', 'Y']], 
                on='Time', 
                direction='nearest'
            )
            
            driver_data.append({
                'id': driver,
                'color': fastf1.plotting.get_driver_color(driver, session=session),
                'x': merged['X'].to_numpy(),
                'y': merged['Y'].to_numpy()
            })
        except:
            continue

    # 5. Visual Setup (Neon Style)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('off')
    # Set background to dark
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')

    # Static Track Map
    ref = driver_data[0]
    ax.plot(ref['x'], ref['y'], color='#222222', linewidth=6, zorder=1)

    # Dynamic Elements
    cars = []
    texts = []
    for d in driver_data:
        # Car Dot
        dot, = ax.plot([], [], 'o', color=d['color'], markersize=8, 
                       markeredgecolor='white', markeredgewidth=1, zorder=5)
        cars.append(dot)
        # Driver Label
        txt = ax.text(0, 0, d['id'], color='white', fontsize=8, fontweight='bold', zorder=6)
        texts.append(txt)

    ax.set_title(f"Lap {target_lap} Replay - Round {round_num}", color='white', fontsize=12)

    # 6. Animation Function
    def update(frame):
        updated_artists = []
        for i, d in enumerate(driver_data):
            if frame < len(d['x']):
                x, y = d['x'][frame], d['y'][frame]
                cars[i].set_data([x], [y])
                texts[i].set_position((x + 60, y + 60))
                updated_artists.append(cars[i])
                updated_artists.append(texts[i])
        return updated_artists

    # 7. Generate HTML (No FFmpeg required)
    ani = animation.FuncAnimation(fig, update, frames=len(common_time), blit=True, interval=100)
    
    # Close plot to prevent static display
    plt.close(fig)
    
    # return the HTML string directly
    return ani.to_jshtml()
