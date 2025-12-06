import fastf1
import pandas as pd
import os

# Setup Cache
if not os.path.exists('f1_cache'):
    os.makedirs('f1_cache')
fastf1.Cache.enable_cache('f1_cache')

def get_season_schedule(year=2025):
    """Fetches the list of all races for the given year."""
    print(f"Fetching schedule for {year}...")
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    # Filter for races that have already happened (or are scheduled)
    return schedule

def collect_full_season_data(year=2025):
    """Loops through every race and saves the results to CSV."""
    schedule = get_season_schedule(year)
    all_results = []
    
    print(f"\n--- STARTING DATA COLLECTION FOR {year} ---")
    print(f"Found {len(schedule)} rounds. This may take time.\n")

    for i, row in schedule.iterrows():
        round_num = row['RoundNumber']
        country = row['Country']
        location = row['Location']
        
        # skip if no official session name (usually means canceled/future without data)
        if not row['Session5']: 
            continue

        print(f"Processing Round {round_num}: {country} ({location})...")
        
        try:
            # Load the Race Session ('R')
            session = fastf1.get_session(year, round_num, 'R')
            session.load(laps=False, telemetry=False) # Load only results to be faster
            
            # Extract results
            results = session.results
            
            # Save relevant data for each driver
            for driver_code, data in results.iterrows():
                all_results.append({
                    'Round': round_num,
                    'Country': country,
                    'Location': location,
                    'Driver': data['Abbreviation'], # e.g., VER
                    'Team': data['TeamName'],
                    'Position': data['Position'],
                    'Points': data['Points'],
                    'GridPosition': data['GridPosition'],
                    'Status': data['Status'] # e.g., Finished, Crash
                })
                
        except Exception as e:
            # Simplified print to avoid encoding errors
            print(f"  -> Could not load data for {country}: {e}")

    # Convert to DataFrame and Save
    if all_results:
        df = pd.DataFrame(all_results)
        csv_filename = f'f1_season_{year}_data.csv'
        df.to_csv(csv_filename, index=False)
        # REMOVED EMOJI HERE to fix crash
        print(f"\n[SUCCESS] Data saved to '{csv_filename}'")
        return df
    else:
        print("\n[WARNING] No results found. The season might not have started yet.")
        return pd.DataFrame()