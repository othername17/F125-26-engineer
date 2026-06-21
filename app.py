import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

# Configuration
MAPS_DIR = "maps"
if not os.path.exists(MAPS_DIR):
    os.makedirs(MAPS_DIR)

# Function to retrieve the Master Map
def get_master_map(track_id):
    map_path = os.path.join(MAPS_DIR, f"{track_id}.csv")
    if os.path.exists(map_path):
        return pd.read_csv(map_path, sep='\t')
    return None

st.set_page_config(layout="wide")
st.title("Racing Telemetry Analyzer")

# File uploader
uploaded_file = st.file_uploader("Upload your hot lap session", type=["csv"])

if uploaded_file is not None:
    # Read the session data
    session_df = pd.read_csv(uploaded_file, sep='\t')
    
    # Extract trackId
    track_id = int(session_df['trackId'].iloc[0])
    
    # Attempt to load the Master Map
    master_map = get_master_map(track_id)
    
    if master_map is not None:
        st.success(f"Master Map found for Track ID: {track_id}")
        
        # Visualization
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Draw the Master Map (Ground Truth)
        ax.plot(master_map['world_position_X'], master_map['world_position_Z'], 
                color='white', alpha=0.5, linewidth=2, label="Master Map (Ground Truth)")
        
        # Draw session data (Overlay)
        ax.scatter(session_df['world_position_X'], session_df['world_position_Z'], 
                   s=1, c='cyan', alpha=0.8, label="Session Data")
        
        # Styling
        ax.set_facecolor('#111111')
        fig.patch.set_facecolor('#111111')
        ax.tick_params(colors='white')
        ax.legend(loc='upper right')
        ax.axis('equal')
        
        st.pyplot(fig)
    else:
        st.error(f"Missing Master Map. Please place '{track_id}.csv' in the '/maps' folder.")
