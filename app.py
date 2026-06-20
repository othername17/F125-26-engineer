import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="F1 Virtual Race Engineer", layout="wide")
st.title("F1 25/26 Virtual Race Engineer")

uploaded_file = st.file_uploader("Upload Telemetry CSV (SRT format)", type=['csv'])

@st.cache_data
def load_data(file):
    if file is not None:
        try:
            df = pd.read_csv(file, sep='\t')
            
            if 'validBin' in df.columns:
                df = df[df['validBin'] == 1]
            
            if all(col in df.columns for col in ['velocity_X', 'velocity_Y', 'velocity_Z']):
                df['speed_kmh'] = np.sqrt(df['velocity_X']**2 + df['velocity_Y']**2 + df['velocity_Z']**2) * 3.6
            
            return df
        except Exception as e:
            st.error(f"Error loading file: {e}")
            return None
    return None

def analyze_track_map(df):
    track_dict = {
        0: "Melbourne", 1: "Paul Ricard", 2: "Shanghai", 3: "Bahrain",
        4: "Catalunya", 5: "Monaco", 6: "Montreal", 7: "Silverstone",
        8: "Hockenheim", 9: "Hungaroring", 10: "Spa-Francorchamps", 11: "Monza",
        12: "Singapore", 13: "Suzuka", 14: "Abu Dhabi", 15: "COTA (Texas)",
        16: "Brazil", 17: "Austria", 18: "Sochi", 19: "Mexico",
        20: "Baku",
