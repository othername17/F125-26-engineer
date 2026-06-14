import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="F1 Virtual Race Engineer", layout="wide")
st.title("F1 25/26 Virtual Race Engineer")

uploaded_file = st.file_uploader("Upload Telemetry CSV", type=['csv'])

@st.cache_data
def load_data(file):
    if file is not None:
        try:
            return pd.read_csv(file)
        except Exception as e:
            st.error(f"Error loading file: {e}")
            return None
    return None

if uploaded_file is not None:
    telemetry_df = load_data(uploaded_file)
    if telemetry_df is not None:
        st.success("Telemetry data loaded successfully.")
else:
    st.info("Please upload your telemetry CSV to begin.")
  def analyze_braking_and_entry(df):
    st.subheader("1. Braking & Corner Entry Diagnostics")
    issues_found = False

    # Note: Column names ('brake', 'speed', 'wheel_speed_fl', etc.) and thresholds 
    # (0.8, 15, 1.5) are placeholders and will need adjustment to match your exact CSV headers and game telemetry scale.

    # Front Wheel Lockup
    front_lockup = df[(df['brake'] > 0.8) & 
                      (df['speed'] > 50) & 
                      ((df['speed'] - df[['wheel_speed_fl', 'wheel_speed_fr']].mean(axis=1)) > 15)]
    
    if not front_lockup.empty:
        issues_found = True
        st.warning("⚠️ **Front Wheel Lockup Detected**")
        st.write("**In-Game Solution:** Shift Brake Bias rearward; decrease Brake Pressure.")

    # Rear Lockup / Entry Snap Oversteer
    rear_lockup = df[(df['brake'] > 0.6) & 
                     ((df['speed'] - df[['wheel_speed_rl', 'wheel_speed_rr']].mean(axis=1)) > 15) & 
                     (abs(df['yaw_rate']) > 1.5)]
    
    if not rear_lockup.empty:
        issues_found = True
        st.warning("⚠️ **Rear Lockup / Entry Snap Oversteer Detected**")
        st.write("**In-Game Solution:** Shift Brake Bias forward; decrease Engine Braking.")

    # Entry Understeer (Refusal to turn)
    entry_understeer = df[(df['brake'] > 0.1) & 
                          (abs(df['steer']) > 0.6) & 
                          (abs(df['lat_g']) < 1.0) & 
                          (df['speed'] > 80)]
    
    if not entry_understeer.empty:
        issues_found = True
        st.warning("⚠️ **Entry Understeer (Refusal to turn) Detected**")
        st.write("**In-Game Solution:** Increase Front Wing; soften Front Suspension; increase Front Toe-Out.")

    if not issues_found:
        st.success("No Braking & Corner Entry issues detected.")

# To integrate with the previous block:
# if telemetry_df is not None:
#     analyze_braking_and_entry(telemetry_df)
def analyze_mid_corner_balance(df):
    st.subheader("2. Mid-Corner Balance Diagnostics")
    issues_found = False

    # Mid-Corner Understeer
    mid_understeer = df[(df['throttle'] < 0.05) & 
                        (df['brake'] < 0.05) & 
                        (abs(df['steer']) > 0.6) & 
                        (abs(df['yaw_rate']) < 1.0) & 
                        (df['speed'] > 50)]
    
    if not mid_understeer.empty:
        issues_found = True
        st.warning("⚠️ **Mid-Corner Understeer Detected**")
        st.write("**In-Game Solution:** Decrease Off-Throttle Differential; soften Front Anti-Roll Bar.")

    # Mid-Corner Oversteer
    mid_oversteer = df[(df['throttle'] < 0.05) & 
                       (df['brake'] < 0.05) & 
                       (abs(df['yaw_rate']) > 1.8)]
    
    if not mid_oversteer.empty:
        issues_found = True
        st.warning("⚠️ **Mid-Corner Oversteer Detected**")
        st.write("**In-Game Solution:** Increase Off-Throttle Differential; stiffen Front Anti-Roll Bar.")

    if not issues_found:
        st.success("No Mid-Corner Balance issues detected.")


def analyze_corner_exit(df):
    st.subheader("3. Corner Exit & Traction Diagnostics")
    issues_found = False

    # Power Oversteer (Traction Loss)
    power_oversteer = df[(df['throttle'] > 0.4) & 
                         ((df[['wheel_speed_rl', 'wheel_speed_rr']].mean(axis=1) - df['speed']) > 15) & 
                         (abs(df['yaw_rate']) > 1.5)]
    
    if not power_oversteer.empty:
        issues_found = True
        st.warning("⚠️ **Power Oversteer (Traction Loss) Detected**")
        st.write("**In-Game Solution:** Decrease On-Throttle Differential; soften Rear Suspension; decrease Rear Tyre Pressures.")

    # On-Throttle Understeer
    on_throttle_understeer = df[(df['throttle'] > 0.2) & 
                                (abs(df['steer']) > 0.6) & 
                                (abs(df['lat_g']) < 1.0) & 
                                (df['speed'] > 60)]
    
    if not on_throttle_understeer.empty:
        issues_found = True
        st.warning("⚠️ **On-Throttle Understeer Detected**")
        st.write("**In-Game Solution:** Increase On-Throttle Differential; increase Front Wing; stiffen Rear Anti-Roll Bar.")

    if not issues_found:
        st.success("No Corner Exit & Traction issues detected.")

# To integrate with the previous block:
# if telemetry_df is not None:
#     analyze_braking_and_entry(telemetry_df)
#     analyze_mid_corner_balance(telemetry_df)
#     analyze_corner_exit(telemetry_df)
def analyze_aerodynamics(df):
    st.subheader("4. Aerodynamics & Straight-Line Speed")
    issues_found = False

    # High Drag / Straight-Line Speed Deficit
    # Assuming top gear is 8 and max RPM is roughly 11500+
    high_drag = df[(df['gear'] == 8) & 
                   (df['rpm'] > 11500) & 
                   (df['speed'] < df['speed'].max() * 0.95)]
    
    if not high_drag.empty:
        issues_found = True
        st.warning("⚠️ **High Drag / Straight-Line Speed Deficit Detected**")
        st.write("**In-Game Solution:** Decrease Front Wing; decrease Rear Wing.")

    if not issues_found:
        st.success("No Aerodynamics & Straight-Line Speed issues detected.")


def analyze_chassis_dynamics(df):
    st.subheader("5. Chassis Dynamics & Ride Quality")
    issues_found = False

    # Bottoming Out
    bottoming_out = df[(df['speed'] > 200) & 
                       ((df['susp_travel_fl'] <= 0.0) | (df['susp_travel_fr'] <= 0.0) | 
                        (df['susp_travel_rl'] <= 0.0) | (df['susp_travel_rr'] <= 0.0)) & 
                       (abs(df['vert_g']) > 2.0)]
    
    if not bottoming_out.empty:
        issues_found = True
        st.warning("⚠️ **Bottoming Out Detected**")
        st.write("**In-Game Solution:** Increase Ride Height (Front/Rear); stiffen Suspension.")

    # Kerb Instability / Bouncing
    kerb_instability = df[(abs(df['vert_g'].diff()) > 1.5) & 
                          (abs(df[['wheel_speed_fl', 'wheel_speed_fr', 'wheel_speed_rl', 'wheel_speed_rr']].diff().max(axis=1)) > 5) &
                          (df['speed'] > 80)]
    
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
    # Temp thresholds will need mapping to game's optimal windows (e.g., > 105C)
    overheating = df[df[['tyre_temp_fl', 'tyre_temp_fr', 'tyre_temp_rl', 'tyre_temp_rr']].max(axis=1) > 105]
    
    if not overheating.empty:
        issues_found = True
        st.warning("⚠️ **Overall Tyre Overheating Detected**")
        st.write("**In-Game Solution:** Decrease Tyre Pressures.")

    # Uneven Tyre Temperature Distribution
    # Relies on inner and outer temp telemetry columns
    uneven_temps = df[(abs(df['tyre_temp_inner_fl'] - df['tyre_temp_outer_fl']) > 10) |
                      (abs(df['tyre_temp_inner_fr'] - df['tyre_temp_outer_fr']) > 10) |
                      (abs(df['tyre_temp_inner_rl'] - df['tyre_temp_outer_rl']) > 10) |
                      (abs(df['tyre_temp_inner_rr'] - df['tyre_temp_outer_rr']) > 10)]
    
    if not uneven_temps.empty:
        issues_found = True
        st.warning("⚠️ **Uneven Tyre Temperature Distribution Detected**")
        st.write("**In-Game Solution:** Adjust Camber (reduce negative camber if inner is too hot); adjust Toe.")

    # High Tyre Wear Rates
    # Checks for rapid degradation (e.g., > 50% wear over the loaded dataset)
    high_wear = df[df[['tyre_wear_fl', 'tyre_wear_fr', 'tyre_wear_rl', 'tyre_wear_rr']].max(axis=1) > 50]
    
    if not high_wear.empty:
        issues_found = True
        st.warning("⚠️ **High Tyre Wear Rates Detected**")
        st.write("**In-Game Solution:** Decrease Tyre Pressures; reduce Camber and Toe angles; soften Suspension.")

    if not issues_found:
        st.success("No Tyre Temperature & Wear issues detected.")

# To integrate:
# if telemetry_df is not None:
#     ...
#     analyze_aerodynamics(telemetry_df)
#     analyze_chassis_dynamics(telemetry_df)
#     analyze_tyres(telemetry_df)
def analyze_brake_temperatures(df):
    st.subheader("7. Brake Temperatures")
    issues_found = False

    # Temperature thresholds (e.g., > 1000C and < 400C) are placeholders
    overheating = df[df[['brake_temp_fl', 'brake_temp_fr', 'brake_temp_rl', 'brake_temp_rr']].max(axis=1) > 1000]
    
    if not overheating.empty:
        issues_found = True
        st.warning("⚠️ **Brake Overheating Detected**")
        st.write("**In-Game Solution:** Decrease Brake Pressure; adjust Brake Bias away from the overheating axle.")

    # Using max() here to check if ALL brakes are too cold, or could use min() if any brake is cold
    cold_brakes = df[df[['brake_temp_fl', 'brake_temp_fr', 'brake_temp_rl', 'brake_temp_rr']].max(axis=1) < 400]
    
    if not cold_brakes.empty:
        issues_found = True
        st.warning("⚠️ **Cold Brakes Detected**")
        st.write("**In-Game Solution:** Increase Brake Pressure; adjust Brake Bias toward the cold axle.")

    if not issues_found:
        st.success("No Brake Temperature issues detected.")


def analyze_fuel_and_weight(df):
    st.subheader("8. Fuel & Weight")
    issues_found = False

    # Placeholder logic: Checks for slow lap times paired with high fuel remaining at the end of the dataset
    excess_fuel = df[(df['speed'] < df['speed'].max() * 0.9) & 
                     (df['fuel_remaining'] > 5.0)] # 5.0 is a placeholder threshold
    
    if not excess_fuel.empty:
        issues_found = True
        st.warning("⚠️ **Excessive Weight Detected**")
        st.write("**In-Game Solution:** Decrease Fuel Load.")

    if not issues_found:
        st.success("No Fuel & Weight issues detected.")


def analyze_data_integrity(df):
    st.subheader("9. Data Integrity Check")
    
    # Calculate the step differences in pedal inputs to check for perfectly even spacing (quantization)
    throttle_diff = df['throttle'].diff().dropna()
    brake_diff = df['brake'].diff().dropna()
    
    # Isolate active pedal movements by removing instances where the pedal is held steady
    throttle_changes = throttle_diff[throttle_diff != 0]
    brake_changes = brake_diff[brake_diff != 0]
    
    # A variance near zero indicates perfectly even, rhythmic patterns without human micro-variations
    throttle_quantized = not throttle_changes.empty and throttle_changes.var() < 1e-6
    brake_quantized = not brake_changes.empty and brake_changes.var() < 1e-6
    
    if throttle_quantized or brake_quantized:
        st.error("🚨 **Spoofed / Automated Inputs Detected**")
        st.write("**Telemetry Trigger:** Traces manifest as perfectly even spacing due to quantization, lacking human micro-variations.")
        st.write("**System Action:** Lap data flagged as invalid. Halting setup recommendations.")
        return False
    
    st.success("Data Integrity Check passed. No spoofed inputs detected.")
    return True

# To integrate all modules together in the main execution block:
# if telemetry_df is not None:
#     data_valid = analyze_data_integrity(telemetry_df)
#     if data_valid:
#         analyze_braking_and_entry(telemetry_df)
#         analyze_mid_corner_balance(telemetry_df)
#         analyze_corner_exit(telemetry_df)
#         analyze_aerodynamics(telemetry_df)
#         analyze_chassis_dynamics(telemetry_df)
#         analyze_tyres(telemetry_df)
#         analyze_brake_temperatures(telemetry_df)
#         analyze_fuel_and_weight(telemetry_df)
