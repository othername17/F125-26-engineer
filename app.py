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
    front_wheel_speed = df[['wheel_speed_2', 'wheel_speed_3']].mean(axis=1) * 3.6
    rear_wheel_speed = df[['wheel_speed_0', 'wheel_speed_1']].mean(axis=1) * 3.6
    front_lockup = df[(df['brake'] > 0.8) & (df['speed_kmh'] > 50) & ((df['speed_kmh'] - front_wheel_speed) > 15)]
    rear_lockup = df[(df['brake'] > 0.6) & ((df['speed_kmh'] - rear_wheel_speed) > 15) & (abs(df['angular_vel_Y']) > 1.0)]
    entry_understeer = df[(df['brake'] > 0.1) & (abs(df['steering']) > 0.75) & (abs(df['gforce_X']) < 1.0) & (df['speed_kmh'] > 80)]
    
    if not front_lockup.empty:
        st.warning(f"⚠️ Front Wheel Lockup Detected ({len(front_lockup)} frames)")
        st.info("Alternatives: 1. Brake Bias rearward. 2. Less brake pressure. 3. Earlier braking.")
    if not rear_lockup.empty:
        st.warning(f"⚠️ Rear Lockup Detected ({len(rear_lockup)} frames)")
        st.info("Alternatives: 1. Brake Bias forward. 2. Soften rear suspension. 3. Adjust engine braking.")
    if not entry_understeer.empty:
        st.warning(f"⚠️ Entry Understeer Detected ({len(entry_understeer)} frames)")
        st.info("Alternatives: 1. More front wing. 2. Soften front ARB. 3. More trail braking.")
    if front_lockup.empty and rear_lockup.empty and entry_understeer.empty:
        st.success("No Braking & Corner Entry issues detected.")

def analyze_mid_corner_balance(df):
    st.subheader("2. Mid-Corner Balance Diagnostics")
    mid_understeer = df[(df['throttle'] < 0.05) & (df['brake'] < 0.05) & (abs(df['steering']) > 0.6) & (abs(df['angular_vel_Y']) < 0.5) & (df['speed_kmh'] > 50)]
    mid_oversteer = df[(df['throttle'] < 0.05) & (df['brake'] < 0.05) & (abs(df['angular_vel_Y']) > 1.5)]
    
    if not mid_understeer.empty:
        st.warning(f"⚠️ Mid-Corner Understeer Detected ({len(mid_understeer)} frames)")
        st.info("Alternatives: 1. Soften front ARB. 2. Stiffen rear ARB. 3. Less front wing.")
    if not mid_oversteer.empty:
        st.warning(f"⚠️ Mid-Corner Oversteer Detected ({len(mid_oversteer)} frames)")
        st.info("Alternatives: 1. Stiffen front ARB. 2. Soften rear ARB. 3. More rear wing.")
    if mid_understeer.empty and mid_oversteer.empty:
        st.success("No Mid-Corner Balance issues detected.")

def analyze_corner_exit(df):
    st.subheader("3. Corner Exit & Traction Diagnostics")
    rear_wheel_speed = df[['wheel_speed_0', 'wheel_speed_1']].mean(axis=1) * 3.6
    power_oversteer = df[(df['throttle'] > 0.4) & ((rear_wheel_speed - df['speed_kmh']) > 8) & (abs(df['angular_vel_Y']) > 1.2)]
    on_throttle_understeer = df[(df['throttle'] > 0.2) & (abs(df['steering']) > 0.6) & (abs(df['gforce_X']) < 1.0) & (df['speed_kmh'] > 60)]
    
    if not power_oversteer.empty:
        st.warning(f"⚠️ Power Oversteer Detected ({len(power_oversteer)} frames)")
        st.info("Alternatives: 1. Soften rear suspension. 2. More rear wing. 3. Smoother throttle.")
    if not on_throttle_understeer.empty:
        st.warning(f"⚠️ On-Throttle Understeer Detected ({len(on_throttle_understeer)} frames)")
        st.info("Alternatives: 1. Stiffen rear ARB. 2. Less front wing. 3. Check diff settings.")
    if power_oversteer.empty and on_throttle_understeer.empty:
        st.success("No Corner Exit & Traction issues detected.")

def analyze_aerodynamics(df):
    st.subheader("4. Aerodynamics & Straight-Line Speed")
    high_drag = df[(df['gear'] == 8) & (df['speed_kmh'] < df['speed_kmh'].max() * 0.95)]
    if not high_drag.empty:
        st.warning(f"⚠️ High Drag Detected ({len(high_drag)} frames)")
        st.info("Alternatives: 1. Less front wing. 2. Less rear wing.")
    else: st.success("No Aerodynamics issues detected.")

def analyze_chassis_dynamics(df):
    st.subheader("5. Chassis Dynamics & Ride Quality")
    bottoming_out = df[(df['speed_kmh'] > 200) & ((df['susp_pos_0'] < 0.15) | (df['susp_pos_1'] < 0.15) | (df['susp_pos_2'] < 0.15) | (df['susp_pos_3'] < 0.15)) & (abs(df['gforce_Z']) > 5.0)]
    kerb_instability = df[(abs(df['gforce_Y'].diff()) > 2.0) & (abs(df[['wheel_speed_0', 'wheel_speed_1', 'wheel_speed_2', 'wheel_speed_3']].diff().max(axis=1)) > 1.5) & (df['speed_kmh'] > 80)]
    
    if not bottoming_out.empty:
        st.warning("⚠️ Bottoming Out Detected")
        st.info("Alternatives: 1. Higher ride height. 2. Stiffer suspension.")
    if not kerb_instability.empty:
        st.warning("⚠️ Kerb Instability Detected")
        st.info("Alternatives: 1. Softer suspension. 2. Softer ARBs.")
    if bottoming_out.empty and kerb_instability.empty:
        st.success("No Chassis Dynamics issues detected.")

def analyze_tyres(df):
    st.subheader("6. Tyre Temperatures & Wear")
    overheating = df[['tyre_temp_0', 'tyre_temp_1', 'tyre_temp_2', 'tyre_temp_3']].max(axis=1).max() > 105
    high_wear = df[['tyre_wear_0', 'tyre_wear_1', 'tyre_wear_2', 'tyre_wear_3']].max(axis=1).max() > 50
    
    if overheating:
        st.warning("⚠️ Tyre Overheating Detected")
        st.info("Alternatives: 1. Lower pressures. 2. Less aggressive driving.")
    if high_wear:
        st.warning("⚠️ High Tyre Wear Detected")
        st.info("Alternatives: 1. Less camber. 2. Less toe.")
    if not overheating and not high_wear:
        st.success("No Tyre Temperature & Wear issues detected.")

def analyze_brake_temperatures(df):
    st.subheader("7. Brake Temperatures")
    max_temp = df[['brake_temp_0', 'brake_temp_1', 'brake_temp_2', 'brake_temp_3']].max(axis=1).max()
    if max_temp > 1000:
        st.warning("⚠️ Brake Overheating Detected")
        st.info("Alternatives: 1. Adjust brake bias. 2. Manage braking points.")
    elif max_temp < 400:
        st.warning("⚠️ Cold Brakes Detected")
        st.info("Alternatives: 1. More aggressive braking. 2. Check brake bias.")
    else: st.success("No Brake Temperature issues detected.")

def analyze_fuel_and_weight(df):
    st.subheader("8. Fuel & Weight")
    if (df['speed_kmh'].max() * 0.9 > df['speed_kmh'].min()) and (df['fuel'].max() > 10.0):
        st.warning("⚠️ Excessive Weight Detected")
    else: st.success("No Fuel & Weight issues detected.")

def analyze_data_integrity(df):
    st.subheader("9. Data Integrity Check")
    throttle_changes = df['throttle'].diff().dropna()
    brake_changes = df['brake'].diff().dropna()
    if (not throttle_changes.empty and throttle_changes.var() < 1e-6) or (not brake_changes.empty and brake_changes.var() < 1e-6):
        st.error("🚨 Spoofed/Automated Inputs Detected")
        return False
    st.success("Data Integrity Check passed.")
    return True

if uploaded_file is not None:
    telemetry_df = load_data(uploaded_file)
    if telemetry_df is not None:
        if analyze_data_integrity(telemetry_df):
            analyze_braking_and_entry(telemetry_df)
            analyze_mid_corner_balance(telemetry_df)
            analyze_corner_exit(telemetry_df)
            analyze_aerodynamics(telemetry_df)
            analyze_chassis_dynamics(telemetry_df)
            analyze_tyres(telemetry_df)
            analyze_brake_temperatures(telemetry_df)
            analyze_fuel_and_weight(telemetry_df)
else: st.info("Please upload your telemetry CSV to begin.")
