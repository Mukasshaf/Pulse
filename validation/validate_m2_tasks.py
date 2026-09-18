import pandas as pd
import numpy as np

def validate_task3(file_path):
    print(f"--- Task 3: Motion Artifact Flagging ({file_path}) ---")
    df = pd.read_csv(file_path)
    
    # Calculate magnitude of acceleration
    df['acc_mag'] = np.sqrt(df['acc_x']**2 + df['acc_y']**2 + df['acc_z']**2)
    
    # Calculate rolling 1s std (66.67 Hz = ~67 samples)
    df['acc_std'] = df['acc_mag'].rolling(window=67).std()
    
    start_time = df['timestamp_ms'].iloc[0]
    df['time_sec'] = (df['timestamp_ms'] - start_time) / 1000.0
    
    rest_mask = (df['time_sec'] < 20) | (df['time_sec'] > 40)
    motion_mask = (df['time_sec'] >= 20) & (df['time_sec'] <= 40)
    
    rest_std_mean = df.loc[rest_mask, 'acc_std'].mean()
    motion_std_mean = df.loc[motion_mask, 'acc_std'].mean()
    motion_std_max = df.loc[motion_mask, 'acc_std'].max()
    
    print(f"Resting baseline ACC std (mean): {rest_std_mean:.2f}")
    print(f"Tapping window ACC std (mean): {motion_std_mean:.2f}")
    print(f"Tapping window ACC std (max): {motion_std_max:.2f}")
    
    if rest_std_mean > 0:
        ratio = motion_std_max / rest_std_mean
        print(f"Difference ratio (Max Motion Std / Mean Rest Std): {ratio:.2f}x")
        if ratio > 3:
            print("Result: [PASS] - Clear spike detected!")
        else:
            print("Result: [FAIL] - No statistically clear spike detected (>3x).")
    else:
        print("Rest std is 0.")

def validate_task4(file_path):
    print(f"\n--- Task 4: Drop Rate ({file_path}) ---")
    df = pd.read_csv(file_path)
    
    first_ts = df['timestamp_ms'].iloc[0]
    last_ts = df['timestamp_ms'].iloc[-1]
    duration_ms = last_ts - first_ts
    
    expected_rows = int(duration_ms / 15) + 1
    actual_rows = len(df)
    
    gap_count = (df['sample_idx'].diff() != 1).sum() - 1 
    
    drop_rate = 1.0 - (actual_rows / expected_rows) if expected_rows > 0 else 0
    drop_rate_pct = drop_rate * 100
    
    print(f"Duration: {duration_ms/1000:.3f} s")
    print(f"Expected rows: {expected_rows}")
    print(f"Actual rows: {actual_rows}")
    print(f"Gap events (idx diff != 1): {gap_count}")
    print(f"Drop rate: {drop_rate_pct:.3f}%")
    
    if drop_rate_pct < 5.0:
        print("Result: [PASS] - Drop rate < 5%")
    else:
        print("Result: [FAIL] - Drop rate >= 5%")

validate_task3('recorded_data_60s_moving1.csv')
validate_task3('recorded_data_60s_moving2.csv')
validate_task3('recorded_data_60s_moving3.csv')
validate_task4('recorded_data_120s.csv')
validate_task4('recorded_data_300s.csv')
validate_task4('recorded_data_300s_2.csv')
