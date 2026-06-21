import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

track_dict = {
    0: "Melbourne", 1: "Paul Ricard", 2: "Shanghai", 3: "Bahrain",
    4: "Catalunya", 5: "Monaco", 6: "Montreal", 7: "Silverstone",
    8: "Hockenheim", 9: "Hungaroring", 10: "Spa-Francorchamps", 11: "Monza",
    12: "Singapore", 13: "Suzuka", 14: "Abu Dhabi", 15: "COTA (Texas)",
    16: "Brazil", 17: "Austria", 18: "Sochi", 19: "Mexico",
    20: "Baku", 21: "Sakhir Short", 22: "Silverstone Short", 23: "Texas Short",
    24: "Suzuka Short", 25: "Hanoi", 26: "Zandvoort", 27: "Imola",
    28: "Portimão", 29: "Jeddah", 30: "Miami", 31: "Las Vegas", 32: "Losail"
}

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

def analyze_braking_and_entry(df):
    st.subheader("1. Braking & Corner Entry Diagnostics")
    issues_found = False
    front_wheel_speed = df[['wheel_speed_2', 'wheel_speed_3']].mean(axis=1) * 3.6
    rear_wheel_speed = df[['wheel_speed_0', 'wheel_speed_1']].mean(axis=1) * 3.6
    front_lockup = df[(df['brake'] > 0.8) & (df['speed_kmh'] > 50) & ((df['speed_kmh'] - front_wheel_speed) > 15)]
    if not front_lockup.empty:
        issues_found = True
        st.warning(f"⚠️ Front Wheel Lockup Detected ({len(front_lockup)} frames)")
        st.info("Suggestion: Move brake bias rearward.")
    if not issues_found: st.success("No Braking & Corner Entry issues detected.")

def analyze_data_integrity(df):
    st.subheader("9. Data Integrity Check")
    throttle_diff = df['throttle'].diff().dropna()
    brake_diff = df['brake'].diff().dropna()
    if (not throttle_diff.empty and throttle_diff.var() < 1e-6) or (not brake_diff.empty and brake_diff.var() < 1e-6):
        st.error("🚨 Spoofed/Automated Inputs Detected")
        return False
    st.success("Data Integrity Check passed.")
    return True

if uploaded_file is not None:
    telemetry_df = load_data(uploaded_file)
    if telemetry_df is not None:
        if analyze_data_integrity(telemetry_df):
            analyze_braking_and_entry(telemetry_df)
else: st.info("Please upload your telemetry CSV to begin.")
