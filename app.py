import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. TRACK DICTIONARY ---
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
reverse_track_dict = {v: k for k, v in track_dict.items()}

st.set_page_config(page_title="F1 Virtual Race Engineer", layout="wide")

# --- 2. DATA LOADING & FILTERING ---
@st.cache_data
def load_data(file):
    if file is not None:
        try:
            df = pd.read_csv(file, sep='\t')
            if 'validBin' in df.columns:
                df = df[df['validBin'] == 1]
            if all(col in df.columns for col in ['velocity_X', 'velocity_Y', 'velocity_Z']):
                df['speed_kmh'] = np.sqrt(df['velocity_X']**2 + df['velocity_Y']**2 + df['velocity_Z']**2) * 3.6
            df['Issue'] = 'Normal'
            return df
        except Exception as e:
            st.error(f"Error loading file: {e}")
            return None
    return None

def filter_lap(df, lap_num, lap_col):
    if lap_col and lap_num in df[lap_col].unique():
        return df[df[lap_col] == lap_num].reset_index(drop=True)
    return df

# --- 3. DYNAMIC APEX CALCULATION ---
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

# --- 4. PHYSICS DIAGNOSTICS & SETUP SUGGESTIONS ---
def run_all_diagnostics(df):
    st.header("Vehicle Diagnostics & Setup Fixes")
    issues_found = False

    # Braking & Entry
    if all(c in df.columns for c in ['wheel_speed_2', 'wheel_speed_3', 'brake', 'speed_kmh']):
        front_wheel_speed = df[['wheel_speed_2', 'wheel_speed_3']].mean(axis=1) * 3.6
        front_lockup = df[(df['brake'] > 0.8) & (df['speed_kmh'] > 50) & ((df['speed_kmh'] - front_wheel_speed) > 15)]
        if not front_lockup.empty:
            issues_found = True
            st.warning(f"⚠️ **Front Wheel Lockup** ({len(front_lockup)} frames)")
            st.info("🔧 **Fix:** Move Brake Bias rearward (1-2%), decrease Brake Pressure, or stiffen Front Suspension.")
            
    if all(c in df.columns for c in ['brake', 'steering', 'gforce_X', 'speed_kmh']):
        entry_understeer = df[(df['brake'] > 0.1) & (abs(df['steering']) > 0.75) & (abs(df['gforce_X']) < 1.0) & (df['speed_kmh'] > 80)]
        if not entry_understeer.empty:
            issues_found = True
            st.warning(f"⚠️ **Entry Understeer** ({len(entry_understeer)} frames)")
            st.info("🔧 **Fix:** Move Brake Bias rearward, soften Front Anti-Roll Bar, or increase Front Wing aero.")

    # Traction & Exit
    if all(c in df.columns for c in ['wheel_speed_0', 'wheel_speed_1', 'throttle', 'speed_kmh', 'angular_vel_Y']):
        rear_wheel_speed = df[['wheel_speed_0', 'wheel_speed_1']].mean(axis=1) * 3.6
        power_oversteer = df[(df['throttle'] > 0.4) & ((rear_wheel_speed - df['speed_kmh']) > 8) & (abs(df['angular_vel_Y']) > 1.2)]
        if not power_oversteer.empty:
            issues_found = True
            st.warning(f"⚠️ **Power Oversteer / Wheelspin** ({len(power_oversteer)} frames)")
            st.info("🔧 **Fix:** Decrease On-Throttle Differential, soften Rear Suspension, or lower Rear Tire Pressures.")

    # Aero & Chassis
    if all(c in df.columns for c in ['gear', 'speed_kmh']):
        high_drag = df[(df['gear'] == 8) & (df['speed_kmh'] < df['speed_kmh'].max() * 0.95)]
        if not high_drag.empty:
            issues_found = True
            st.warning(f"⚠️ **High Aero Drag** ({len(high_drag)} frames at top gear)")
            st.info("🔧 **Fix:** Lower Rear Wing angle to increase top speed on straights.")

    if all(c in df.columns for c in ['susp_pos_0', 'susp_pos_1', 'susp_pos_2', 'susp_pos_3', 'gforce_Z', 'speed_kmh']):
        bottoming_out = df[(df['speed_kmh'] > 200) & ((df['susp_pos_0'] < 0.15) | (df['susp_pos_1'] < 0.15) | (df['susp_pos_2'] < 0.15) | (df['susp_pos_3'] < 0.15)) & (abs(df['gforce_Z']) > 5.0)]
        if not bottoming_out.empty:
            issues_found = True
            st.warning(f"⚠️ **Chassis Bottoming Out** ({len(bottoming_out)} frames)")
            st.info("🔧 **Fix:** Increase Ride Height (Front/Rear) or stiffen Suspension.")

    if not issues_found:
        st.success("✅ No critical setup issues detected on this lap. Setup is dialed in.")

# --- 5. VISUALIZATION FUNCTIONS ---
def plot_telemetry_traces(df, ref_df=None):
    st.header("Telemetry Traces")
    dist_col = next((col for col in df.columns if 'distance' in col.lower()), df.index)
    
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02, 
                        subplot_titles=("Speed (km/h)", "Throttle", "Brake", "Steering"))

    speed_col = 'speed_kmh' if 'speed_kmh' in df.columns else 'speed'
    
    # Session Traces (Cyan)
    fig.add_trace(go.Scatter(x=df[dist_col], y=df[speed_col], name="Speed", line=dict(color='cyan')), row=1, col=1)
    if 'throttle' in df.columns:
        fig.add_trace(go.Scatter(x=df[dist_col], y=df['throttle'], name="Throttle", line=dict(color='cyan')), row=2, col=1)
    if 'brake' in df.columns:
        fig.add_trace(go.Scatter(x=df[dist_col], y=df['brake'], name="Brake", line=dict(color='cyan')), row=3, col=1)
    if 'steering' in df.columns:
        fig.add_trace(go.Scatter(x=df[dist_col], y=df['steering'], name="Steering", line=dict(color='cyan')), row=4, col=1)

    # Reference Traces (White)
    if ref_df is not None:
        ref_dist_col = next((col for col in ref_df.columns if 'distance' in col.lower()), ref_df.index)
        ref_speed = 'speed_kmh' if 'speed_kmh' in ref_df.columns else 'speed'
        
        if ref_speed in ref_df.columns:
            fig.add_trace(go.Scatter(x=ref_df[ref_dist_col], y=ref_df[ref_speed], name="Ref Speed", line=dict(color='white', dash='dot')), row=1, col=1)
        if 'throttle' in ref_df.columns:
            fig.add_trace(go.Scatter(x=ref_df[ref_dist_col], y=ref_df['throttle'], name="Ref Throttle", line=dict(color='white', dash='dot')), row=2, col=1)
        if 'brake' in ref_df.columns:
            fig.add_trace(go.Scatter(x=ref_df[ref_dist_col], y=ref_df['brake'], name="Ref Brake", line=dict(color='white', dash='dot')), row=3, col=1)
        if 'steering' in ref_df.columns:
            fig.add_trace(go.Scatter(x=ref_df[ref_dist_col], y=ref_df['steering'], name="Ref Steering", line=dict(color='white', dash='dot')), row=4, col=1)

    fig.update_layout(height=800, showlegend=False, hovermode="x unified", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

def analyze_track_map(df, ref_df=None, track_name="Unknown"):
    st.header(f"Track Map Overlay: {track_name}")
    fig = go.Figure()
    
    if 'world_position_X' in df.columns and 'world_position_Z' in df.columns:
        fig.add_trace(go.Scatter(x=df['world_position_X'], y=df['world_position_Z'], name='Session', line=dict(color='cyan')))
        player_apexes = get_dynamic_apexes(df)
        for apex in player_apexes:
            fig.add_annotation(x=apex['x'], y=apex['z'], text=f"{int(apex['speed'])}", showarrow=True, font=dict(color="cyan"))

    if ref_df is not None:
        ref_x = 'world_position_X' if 'world_position_X' in ref_df.columns else 'x'
        ref_z = 'world_position_Z' if 'world_position_Z' in ref_df.columns else 'y'
        if ref_x in ref_df.columns and ref_z in ref_df.columns:
            fig.add_trace(go.Scatter(x=ref_df[ref_x], y=ref_df[ref_z], name='Reference', line=dict(color='white', width=2)))
            ref_apexes = get_dynamic_apexes(ref_df)
            for apex in ref_apexes:
                fig.add_annotation(x=apex['x'], y=apex['z'], text=f"{int(apex['speed'])}", showarrow=True, font=dict(color="white"))

    fig.update_layout(xaxis_title="X", yaxis_title="Z", showlegend=True, height=700, template="plotly_dark")
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    st.plotly_chart(fig, use_container_width=True)

# --- 6. MAIN APP EXECUTION ---
st.title("F1 26 Virtual Race Engineer")

with st.sidebar:
    st.header("Telemetry Input")
    uploaded_file = st.file_uploader("Upload PS5 Telemetry CSV", type=['csv'])

if uploaded_file is not None:
    telemetry_df = load_data(uploaded_file)
    
    if telemetry_df is not None:
        # 1. Isolate the Lap
        lap_cols = [c for c in telemetry_df.columns if 'lap' in c.lower() and 'distance' not in c.lower() and 'time' not in c.lower()]
        lap_col = lap_cols[0] if lap_cols else None
        
        if lap_col:
            laps = sorted(telemetry_df[lap_col].dropna().unique())
            selected_lap = st.sidebar.selectbox("Select Lap to Analyze", options=laps, index=len(laps)-1 if len(laps)>0 else 0)
            analysis_df = filter_lap(telemetry_df, selected_lap, lap_col)
        else:
            st.sidebar.warning("No Lap column detected. Plotting full session.")
            analysis_df = telemetry_df

        # 2. Load the Reference Map
        raw_track_id = analysis_df['trackId'].iloc[0] if 'trackId' in analysis_df.columns else "Unknown"
        track_name_str = str(raw_track_id).strip()
        track_name_display = track_dict.get(int(float(raw_track_id)), track_name_str) if str(raw_track_id).replace('.','',1).isdigit() else track_name_str
        
        map_path_name = f"maps/{track_name_str}.csv"
        clean_track_id = reverse_track_dict.get(track_name_str, track_name_str)
        try:
            clean_track_id = int(float(clean_track_id))
        except (ValueError, TypeError):
            pass
        map_path_id = f"maps/{clean_track_id}.csv"
        
        map_path = map_path_name if os.path.exists(map_path_name) else map_path_id
        ref_df = pd.read_csv(map_path) if os.path.exists(map_path) else None
        
        if ref_df is not None:
            st.sidebar.success(f"Loaded Reference: {map_path}")
        else:
            st.sidebar.info(f"No reference found at {map_path}")

        # 3. Render Everything
        run_all_diagnostics(analysis_df)
        plot_telemetry_traces(analysis_df, ref_df)
        analyze_track_map(analysis_df, ref_df, track_name=track_name_display)

else:
    st.info("Please upload your PS5 telemetry CSV to begin.")
