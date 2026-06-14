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
            # SRT outputs tab-separated files
            df = pd.read_csv(file, sep='\t')
            
            # Filter only valid telemetry frames
            if 'validBin' in df.columns:
                df = df[df['validBin'] == 1]
            
            # Calculate absolute speed in km/h from velocity vectors
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

    # 2=FL, 3=FR, 0=RL, 1=RR (Wheel speeds in m/s converted to km/h)
    front_wheel_speed = df[['wheel_speed_2', 'wheel_speed_3']].mean(axis=1) * 3.6
    rear_wheel_speed = df[['wheel_speed_0', 'wheel_speed_1']].mean(axis=1) * 3.6

    # Front Wheel Lockup
    front_lockup = df[(df['brake'] > 0.8) & 
                      (df['speed_kmh'] > 50) & 
                      ((df['speed_kmh'] - front_wheel_speed) > 15)]
    
    if not front_lockup.empty:
        issues_found = True
        st.warning("⚠️ **Front Wheel Lockup Detected**")
        st.write("**In-Game Solution:** Shift Brake Bias rearward; decrease Brake Pressure.")

    # Rear Lockup / Entry Snap Oversteer
    rear_lockup = df[(df['brake'] > 0.6) & 
                     ((df['speed_kmh'] - rear_wheel_speed) > 15) & 
                     (abs(df['angular_vel_Y']) > 1.0)] # angular_vel_Y = Yaw Rate
    
    if not rear_lockup.empty:
        issues_found = True
        st.warning("⚠️ **Rear Lockup / Entry Snap Oversteer Detected**")
        st.write("**In-Game Solution:** Shift Brake Bias forward; decrease Engine Braking.")

    # Entry Understeer (Refusal to turn)
    entry_understeer = df[(df['brake'] > 0.1) & 
                          (abs(df['steering']) > 0.6) & 
                          (abs(df['gforce_X']) < 1.0) & # gforce_X = Lateral G
                          (df['speed_kmh'] > 80)]
    
    if not entry_understeer.empty:
        issues_found = True
        st.warning("⚠️ **Entry Understeer (Refusal to turn) Detected**")
        st.write("**In-Game Solution:** Increase Front Wing; soften Front Suspension; increase Front Toe-Out.")

    if not issues_found:
        st.success("No Braking & Corner Entry issues detected.")

def analyze_mid_corner_balance(df):
    st.subheader("2. Mid-Corner Balance Diagnostics")
    issues_found = False

    # Mid-Corner Understeer
    mid_understeer = df[(df['throttle'] < 0.05) & 
                        (df['brake'] < 0.05) & 
                        (abs(df['steering']) > 0.6) & 
                        (abs(df['angular_vel_Y']) < 0.5) & 
                        (df['speed_kmh'] > 50)]
    
    if not mid_understeer.empty:
        issues_found = True
        st.warning("⚠️ **Mid-Corner Understeer Detected**")
        st.write("**In-Game Solution:** Decrease Off-Throttle Differential; soften Front Anti-Roll Bar.")

    # Mid-Corner Oversteer
    mid_oversteer = df[(df['throttle'] < 0.05) & 
                       (df['brake'] < 0.05) & 
                       (abs(df['angular_vel_Y']) > 1.5)]
    
    if not mid_oversteer.empty:
        issues_found = True
        st.warning("⚠️ **Mid-Corner Oversteer Detected**")
        st.write("**In-Game Solution:** Increase Off-Throttle Differential; stiffen Front Anti-Roll Bar.")

    if not issues_found:
        st.success("No Mid-Corner Balance issues detected.")

def analyze_corner_exit(df):
    st.subheader("3. Corner Exit & Traction Diagnostics")
    issues_found = False

    rear_wheel_speed = df[['wheel_speed_0', 'wheel_speed_1']].mean(axis=1) * 3.6

    # Power Oversteer (Traction Loss)
    power_oversteer = df[(df['throttle'] > 0.4) & 
                         ((rear_wheel_speed - df['speed_kmh']) > 15) & 
                         (abs(df['angular_vel_Y']) > 1.2)]
    
    if not power_oversteer.empty:
        issues_found = True
        st.warning("⚠️ **Power Oversteer (Traction Loss) Detected**")
        st.write("**In-Game Solution:** Decrease On-Throttle Differential; soften Rear Suspension; decrease Rear Tyre Pressures.")

    # On-Throttle Understeer
    on_throttle_understeer = df[(df['throttle'] > 0.2) & 
                                (abs(df['steering']) > 0.6) & 
                                (abs(df['gforce_X']) < 1.0) & 
                                (df['speed_kmh'] > 60)]
    
    if not on_throttle_understeer.empty:
        issues_found = True
        st.warning("⚠️ **On-Throttle Understeer Detected**")
        st.write("**In-Game Solution:** Increase On-Throttle Differential; increase Front Wing; stiffen Rear Anti-Roll Bar.")

    if not issues_found:
        st.success("No Corner Exit & Traction issues detected.")

def analyze_aerodynamics(df):
    st.subheader("4. Aerodynamics & Straight-Line Speed")
    issues_found = False

    # High Drag / Straight-Line Speed Deficit
    high_drag = df[(df['gear'] == 8) & 
                   (df['rpm'] > 11000) & 
                   (df['speed_kmh'] < df['speed_kmh'].max() * 0.95)]
    
    if not high_drag.empty:
        issues_found = True
        st.warning("⚠️ **High Drag / Straight-Line Speed Deficit Detected**")
        st.write("**In-Game Solution:** Decrease Front Wing; decrease Rear Wing.")

    if not issues_found:
        st.success("No Aerodynamics & Straight-Line Speed issues detected.")

def analyze_chassis_dynamics(df):
    st.subheader("5. Chassis Dynamics & Ride Quality")
    issues_found = False

    # Bottoming Out (gforce_Y is vertical axis, spikes represent bottoming hits)
    bottoming_out = df[(df['speed_kmh'] > 200) & 
                       ((df['susp_pos_0'] < 0.15) | (df['susp_pos_1'] < 0.15) | 
                        (df['susp_pos_2'] < 0.15) | (df['susp_pos_3'] < 0.15)) & 
                       (abs(df['gforce_Y']) > 5.0)]
    
    if not bottoming_out.empty:
        issues_found = True
        st.warning("⚠️ **Bottoming Out Detected**")
        st.write("**In-Game Solution:** Increase Ride Height (Front/Rear); stiffen Suspension.")

    # Kerb Instability / Bouncing
    kerb_instability = df[(abs(df['gforce_Y'].diff()) > 2.0) & 
                          (abs(df[['wheel_speed_0', 'wheel_speed_1', 'wheel_speed_2', 'wheel_speed_3']].diff().max(axis=1)) > 1.5) &
                          (df['speed_kmh'] > 80)]
    
    if not kerb_instability.empty:
        issues_found = True
        st.warning("⚠️ **Kerb Instability / Bouncing Detected**")
        st.write("**In-Game Solution:** Soften Suspension; soften Anti-Roll Bars; increase Ride Height.")

    if not issues_found:
        st.success("No Chassis Dynamics & Ride Quality issues detected.")

def analyze_tyres(df):
    st.subheader("6. Tyre Temperatures & Wear")
    issues_found = False

    # Overall Tyre Overheating
    overheating = df[df[['tyre_temp_0', 'tyre_temp_1', 'tyre_temp_2', 'tyre_temp_3']].max(axis=1) > 105]
    
    if not overheating.empty:
        issues_found = True
        st.warning("⚠️ **Overall Tyre Overheating Detected**")
        st.write("**In-Game Solution:** Decrease Tyre Pressures.")

    # High Tyre Wear Rates
    high_wear = df[df[['tyre_wear_0', 'tyre_wear_1', 'tyre_wear_2', 'tyre_wear_3']].max(axis=1) > 50]
    
    if not high_wear.empty:
        issues_found = True
        st.warning("⚠️ **High Tyre Wear Rates Detected**")
        st.write("**In-Game Solution:** Decrease Tyre Pressures; reduce Camber and Toe angles; soften Suspension.")

    if not issues_found:
        st.success("No Tyre Temperature & Wear issues detected.")

def analyze_brake_temperatures(df):
    st.subheader("7. Brake Temperatures")
    issues_found = False

    # Overheating Brakes
    overheating = df[df[['brake_temp_0', 'brake_temp_1', 'brake_temp_2', 'brake_temp_3']].max(axis=1) > 1000]
    
    if not overheating.empty:
        issues_found = True
        st.warning("⚠️ **Brake Overheating Detected**")
        st.write("**In-Game Solution:** Decrease Brake Pressure; adjust Brake Bias away from the overheating axle.")

    # Cold Brakes
    cold_brakes = df[df[['brake_temp_0', 'brake_temp_1', 'brake_temp_2', 'brake_temp_3']].max(axis=1) < 400]
    
    if not cold_brakes.empty:
        issues_found = True
        st.warning("⚠️ **Cold Brakes Detected**")
        st.write("**In-Game Solution:** Increase Brake Pressure; adjust Brake Bias toward the cold axle.")

    if not issues_found:
        st.success("No Brake Temperature issues detected.")

def analyze_fuel_and_weight(df):
    st.subheader("8. Fuel & Weight")
    issues_found = False

    excess_fuel = df[(df['speed_kmh'] < df['speed_kmh'].max() * 0.9) & 
                     (df['fuel'] > 10.0)] 
    
    if not excess_fuel.empty:
        issues_found = True
        st.warning("⚠️ **Excessive Weight Detected**")
        st.write("**In-Game Solution:** Decrease Fuel Load.")

    if not issues_found:
        st.success("No Fuel & Weight issues detected.")

def analyze_data_integrity(df):
    st.subheader("9. Data Integrity Check")
    
    throttle_diff = df['throttle'].diff().dropna()
    brake_diff = df['brake'].diff().dropna()
    
    throttle_changes = throttle_diff[throttle_diff != 0]
    brake_changes = brake_diff[brake_diff != 0]
    
    throttle_quantized = not throttle_changes.empty and throttle_changes.var() < 1e-6
    brake_quantized = not brake_changes.empty and brake_changes.var() < 1e-6
    
    if throttle_quantized or brake_quantized:
        st.error("🚨 **Spoofed / Automated Inputs Detected**")
        st.write("**Telemetry Trigger:** Traces manifest as perfectly even spacing due to quantization, lacking human micro-variations.")
        st.write("**System Action:** Lap data flagged as invalid. Halting setup recommendations.")
        return False
    
    st.success("Data Integrity Check passed. No spoofed inputs detected.")
    return True

# Main Execution Block
if uploaded_file is not None:
    telemetry_df = load_data(uploaded_file)
    if telemetry_df is not None:
        st.success("Telemetry data loaded successfully.")
        
        data_valid = analyze_data_integrity(telemetry_df)
        if data_valid:
            analyze_braking_and_entry(telemetry_df)
            analyze_mid_corner_balance(telemetry_df)
            analyze_corner_exit(telemetry_df)
            analyze_aerodynamics(telemetry_df)
            analyze_chassis_dynamics(telemetry_df)
            analyze_tyres(telemetry_df)
            analyze_brake_temperatures(telemetry_df)
            analyze_fuel_and_weight(telemetry_df)
else:
    st.info("Please upload your telemetry CSV to begin.")
