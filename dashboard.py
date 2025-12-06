import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import pandas as pd

fastf1.plotting.setup_mpl()

# UPDATE: Added round_num=None
def plot_strategy_dashboard(year=2025, round_num=None):
    print(f"\n--- RACE STRATEGY DASHBOARD ({year}) ---")
    
    if round_num is None:
        raise ValueError("Round Number must be provided for the website.")

    print(f"Loading Strategy Data for Round {round_num}...")
    try:
        session = fastf1.get_session(year, round_num, 'R')
        session.load()
    except Exception as e:
        print(f"Could not load session: {e}")
        return None
    
    laps = session.laps
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    compound_colors = {
        'SOFT': 'red', 'MEDIUM': 'yellow', 'HARD': 'white', 
        'INTERMEDIATE': 'green', 'WET': 'blue'
    }

    try:
        finishing_order = session.results.sort_values(by='Position')['Abbreviation'].tolist()
    except KeyError:
        print("Results not available for sorting.")
        finishing_order = session.drivers

    for i, driver in enumerate(finishing_order):
        driver_laps = laps.pick_driver(driver)
        if driver_laps.empty: continue
        
        stints = driver_laps[['Driver', 'Stint', 'Compound', 'LapNumber']].groupby(['Driver', 'Stint', 'Compound'])
        
        for (d, stint, compound), data in stints:
            min_lap = data['LapNumber'].min()
            max_lap = data['LapNumber'].max()
            c_color = compound_colors.get(compound, 'gray')
            ax.barh(y=i, width=(max_lap - min_lap), left=min_lap, 
                    color=c_color, edgecolor='black', height=0.8)

    ax.set_yticks(range(len(finishing_order)))
    ax.set_yticklabels(finishing_order)
    ax.invert_yaxis()
    ax.set_xlabel("Lap Number")
    ax.set_title(f"Tyre Strategy - {session.event['EventName']}")
    
    print(" > Dashboard Ready. (Close window to finish)")
    return plt.gcf()
