import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import fastf1.plotting

def load_data(year):
    """Loads the CSV data securely."""
    filename = f'f1_season_{year}_data.csv'
    try:
        return pd.read_csv(filename)
    except FileNotFoundError:
        return None

def get_team_color_map():
    """Returns a dictionary of official F1 team colors (Hex codes)."""
    return {
        "Red Bull Racing": "#0600EF",
        "Mercedes": "#0090FF", # Adjusted for visibility on dark mode
        "Ferrari": "#DC0000",
        "McLaren": "#FF8700",
        "Aston Martin": "#006F62",
        "Alpine": "#0090FF",
        "Williams": "#005AFF",
        "Haas F1 Team": "#FFFFFF",
        "Kick Sauber": "#00E701",
        "Racing Bulls": "#1634CC",
    }

def plot_championship_standings(df):
    """Creates an interactive line chart for driver standings."""
    # Aggregate points by round
    df_grouped = df.groupby(['Round', 'Driver', 'Team'])['Points'].sum().reset_index()
    
    # Calculate cumulative sum
    df_grouped.sort_values(by=['Driver', 'Round'], inplace=True)
    df_grouped['Cumulative Points'] = df_grouped.groupby('Driver')['Points'].cumsum()
    
    # Filter top 10 drivers for clarity
    top_drivers = df_grouped.groupby('Driver')['Cumulative Points'].max().nlargest(10).index
    df_filtered = df_grouped[df_grouped['Driver'].isin(top_drivers)]

    # Plot
    fig = px.line(
        df_filtered, 
        x="Round", 
        y="Cumulative Points", 
        color="Driver",
        line_group="Driver",
        hover_data=["Team"],
        markers=True,
        title="🏆 Driver Championship Battle",
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    
    fig.update_layout(
        xaxis_title="Race Round",
        yaxis_title="Total Points",
        hovermode="x unified",
        legend_title_text="",
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Titillium Web", size=14)
    )
    return fig

def plot_team_performance(df):
    """Creates an interactive bar chart for constructor standings."""
    team_points = df.groupby(['Team'])['Points'].sum().reset_index()
    team_points = team_points.sort_values(by='Points', ascending=False)
    
    # Map colors
    color_map = get_team_color_map()
    
    fig = px.bar(
        team_points,
        x="Points",
        y="Team",
        orientation='h',
        color="Team",
        text="Points",
        title="🛠️ Constructor Standings",
        template="plotly_dark",
        color_discrete_map=color_map
    )
    
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="Titillium Web", size=14)
    )
    return fig