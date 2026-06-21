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

def get_dynamic_apexes(df):
    apexes = []
    speed_col = 'speed_kmh' if 'speed_kmh' in df.columns else 'speed'
    if 'steering' in df.columns and speed_col in df.columns:
        turning = abs(df['steering']) > 0.3 
        df['local_min'] = df[speed_col].rolling(window=60, center=True).min()
        apex_points = df[turning & (df[speed_col] == df['local_min'])]
        if not apex_points.empty:
            apex_points = apex_points[apex_points.index.to_series().diff().fillna(51) > 50]
        for _, row in apex_points.iterrows():
            x_col = 'world_position_X' if 'world_position_X' in df.columns else 'x'
            z_col = 'world_position_Z' if 'world_position_Z' in df.columns else 'y'
            apexes.append({'speed': row[speed_col], 'x': row[x_col], 'z': row[z_col]})
    return apexes

def analyze_track_map(df, ref_df=None):
    track_id = df['trackId'].iloc[0] if 'trackId' in df.columns else "Unknown"
    track_name = track_id if isinstance(track_id, str) else track_dict.get(track_id, "Unknown")
    st.subheader(f"10. Track Map Overlay: {track_name}")
    fig = go.Figure()
    if 'world_position_X' in df.columns and 'world_position_Z' in df.columns:
        fig.add_trace(go.Scatter(x=df['world_position_X'], y=df['world_position_Z'], name='Session', line=dict(color='cyan')))
        player_apexes = get_dynamic_apexes(df)
        for apex in player_apexes:
            fig.add_annotation(x=apex['x'], y=apex['z'], text=f"{int(apex['speed'])}kph", showarrow=True, font=dict(color="cyan"))
    if ref_df is not None:
        ref_x = 'world_position_X' if 'world_position_X' in ref_df.columns else 'x'
        ref_z = 'world_position_Z' if 'world_position_Z' in ref_df.columns else 'y'
        if ref_x in ref_df.columns and ref_z in ref_df.columns:
            fig.add_trace(go.Scatter(x=ref_df[ref_x], y=ref_df[ref_z], name='Reference', line=dict(color='white', width=2)))
            ref_apexes = get_dynamic_apexes(ref_df)
            for apex in ref_apexes:
                fig.add_annotation(x=apex['x'], y=apex['z'], text=f"{int(apex['speed'])}kph", showarrow=True, font=dict(color="white"))
    fig.update_layout(xaxis_title="X Position", yaxis_title="Z Position", showlegend=True)
    st.plotly_chart(fig)

def analyze_braking_and_entry(df):
    st.subheader("1. Braking & Corner Entry Diagnostics")
    issues_found = False
    front_wheel_speed = df[['wheel_speed_2', 'wheel_speed_3']].mean(axis=1) * 3.6
    rear_wheel_speed = df[['wheel_speed_0', 'wheel_speed_1']].mean(axis=1) * 3.6
    front_lockup = df[(df['brake'] > 0.8) & (df['speed_kmh'] > 50) & ((df['speed_kmh'] - front_wheel_speed) > 15)]
    if not front_lockup.empty:
        issues_found = True
        st.warning(f"⚠️ **Front Wheel Lockup Detected** ({len(front_lockup)} frames)")
        st.info("💡 **Suggestion:** Move brake bias rearward. Reduce overall brake pressure.")
    rear_lockup = df[(df['brake'] > 0.6) & ((df['speed_kmh'] - rear_wheel_speed) > 15) & (abs(df['angular_vel_Y']) > 1.0)]
    if not rear_lockup.empty:
        issues_found = True
        st.warning(f"⚠️ **Rear Lockup Detected** ({len(rear_lockup)} frames)")
        st.info("💡 **Suggestion:** Move brake bias forward. Increase Off-Throttle Differential.")
    entry_understeer = df[(df['brake'] > 0.1) & (abs(df['steering']) > 0.75) & (abs(df['gforce_X']) < 1.0) & (df['speed_kmh'] > 80)]
    if not entry_understeer.empty:
        issues_found = True
        st.warning(f"⚠️ **Entry Understeer Detected** ({len(entry_understeer)} frames)")
        st.info("💡 **Suggestion:** Increase Front Wing Aero. Soften Front Suspension.")
    if not issues_found: st.success("No Braking & Corner Entry issues detected.")

def analyze_mid_corner_balance(df):
    st.subheader("2. Mid-Corner Balance Diagnostics")
    issues_found = False
    mid_understeer = df[(df['throttle'] < 0.05) & (df['brake'] < 0.05) & (abs(df['steering']) > 0.6) & (abs(df['angular_vel_Y']) < 0.5) & (df['speed_kmh'] > 50)]
    if not mid_understeer.empty:
        issues_found = True
        st.warning(f"⚠️ **Mid-Corner Understeer Detected** ({len(mid_understeer)} frames)")
        st.info("💡 **Suggestion:** Soften Front ARB or stiffen Rear ARB.")
    mid_oversteer = df[(df['throttle'] < 0.05) & (df['brake'] < 0.05) & (abs(df['angular_vel_Y']) > 1.5)]
    if not mid_oversteer.empty:
        issues_found = True
        st.warning(f"⚠️ **Mid-Corner Oversteer Detected** ({len(mid_oversteer)} frames)")
        st.info("💡 **Suggestion:** Stiffen Front ARB or soften Rear ARB.")
    if not issues_found: st.success("No Mid-Corner Balance issues detected.")

def analyze_corner_exit(df):
    st.subheader("3. Corner Exit & Traction Diagnostics")
    issues_found = False
    rear_wheel_speed = df[['wheel_speed_0', 'wheel_speed_1']].mean(axis=1
