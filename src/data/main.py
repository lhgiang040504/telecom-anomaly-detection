from config import Config
from utils import generate_cell_towers, generate_user_profiles

from generators import CallGenerator, SocialStructure, AnomalyInjector
from schemas import CDRSchema, UserSchema

import random
import matplotlib.pyplot as plt
import pandas as pd
import os
import sys
sys.path.insert(0, os.getcwd())
from faker import Faker
fake = Faker('en_IN')

BASE_DIR = sys.path[0]
RAW_DIR = os.path.join(BASE_DIR, "dataset", "raw")

def generate_dataset(output_path=RAW_DIR):
    """
    Generate synthetic CDR dataset with user profiles, 
    social communities, anomalies, and summary plots.
    
    Args:
        output_path (str): where to save the final calls dataset (CSV).
    
    Returns:
        pd.DataFrame: DataFrame of generated call records.
    """
    
    '''_1_'''

    # Social Structure Definition
    social_struct = SocialStructure(Config.NUM_USERS)
    users, communities = social_struct.generate_communities()

    # Cell Tower Generation
    cell_towers = generate_cell_towers(Config.NUM_CELL_TOWERS)
    user_home_cells = {} # Assign home cells to users
    for user in users:
        # Bias assignment based on community (users in same community tend to be in same area)
        user_home_cells[user] = random.choice(cell_towers)['cell_id']

    # User Profile Generation
    user_profiles = generate_user_profiles(users, user_home_cells)
    
    '''_2_'''

    # Generate Complete Dataset
    call_gen = CallGenerator(social_struct, user_profiles, cell_towers)
    normal_calls = call_gen.generate_normal_calls(Config.DAYS)

    # Calculate number of anomalies needed
    total_calls_estimated = len(normal_calls) / (1 - Config.ANOMALY_RATIO)
    num_anomalies = int(total_calls_estimated * Config.ANOMALY_RATIO)
    anomalies_per_type = max(1, num_anomalies // 4)
    print(f"Target anomalies: {num_anomalies} ({anomalies_per_type} per type)")

    # Inject different types of anomalies
    anomaly_injector = AnomalyInjector(social_struct, user_profiles, cell_towers, call_gen)
    short_call_anomalies = anomaly_injector.inject_short_calls(normal_calls, anomalies_per_type)
    long_call_anomalies = anomaly_injector.inject_long_calls(normal_calls, anomalies_per_type)
    off_hour_anomalies = anomaly_injector.inject_off_hour_calls(normal_calls, anomalies_per_type)
    burst_call_anomalies = anomaly_injector.inject_burst_calls(normal_calls, anomalies_per_type)

    # Combine all calls
    all_calls = normal_calls + short_call_anomalies + long_call_anomalies + off_hour_anomalies + burst_call_anomalies

    '''_3_'''

    # Convert to DataFrame
    calls_df = pd.DataFrame(all_calls)

    # Sort by timestamp
    calls_df['call_start_ts'] = pd.to_datetime(calls_df['call_start_ts'])
    calls_df = calls_df.sort_values('call_start_ts').reset_index(drop=True)

    print("Dataset generation completed!")
    print(f"Total calls: {len(calls_df)}")
    print(f"Normal calls: {len(calls_df[calls_df['is_anomaly'] == 0])}")
    print(f"Anomalous calls: {len(calls_df[calls_df['is_anomaly'] == 1])}")
    print("\nAnomaly type distribution:")
    print(calls_df[calls_df['is_anomaly'] == 1]['anomaly_type'].value_counts())
    
    '''_4_'''

    # Save main datasets
    calls_df.to_csv(os.path.join(RAW_DIR, "cdr_call_records.csv"), index=False)
    pd.DataFrame(user_profiles).to_csv(os.path.join(RAW_DIR, "cdr_user_profiles.csv"), index=False)
    pd.DataFrame(cell_towers).to_csv(os.path.join(RAW_DIR, "cdr_cell_towers.csv"), index=False)

    # Save community information (for analysis)
    community_data = []
    for comm_type, communities in social_struct.communities.items():
        for i, comm in enumerate(communities):
            for user in comm:
                community_data.append({
                    'user_id': user,
                    'community_type': comm_type,
                    'community_id': f"{comm_type}_{i}",
                    'community_size': len(comm)
                })
    pd.DataFrame(community_data).to_csv(os.path.join(RAW_DIR, "cdr_communities.csv"), index=False)


    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    calls_df['hour'] = calls_df['call_start_ts'].dt.hour
    axes[0, 0].bar(calls_df['hour'].value_counts().index, calls_df['hour'].value_counts().values, alpha=0.7, color='skyblue')
    axes[0, 0].set_title('Call Distribution by Hour')

    duration_bins = [0, 30, 60, 180, 600, 1800, 3600, calls_df['call_duration'].max()]
    duration_labels = ['<30s', '30-60s', '1-3m', '3-10m', '10-30m', '30-60m', '>1h']
    duration_dist = pd.cut(calls_df['call_duration'], bins=duration_bins, labels=duration_labels).value_counts()
    axes[0, 1].pie(duration_dist.values, labels=duration_dist.index, autopct='%1.1f%%')
    axes[0, 1].set_title('Call Duration Distribution')

    anomaly_counts = calls_df[calls_df['is_anomaly'] == 1]['anomaly_type'].value_counts()
    axes[1, 0].bar(anomaly_counts.index, anomaly_counts.values, color='salmon')
    axes[1, 0].set_title('Anomaly Type Distribution')

    calls_df['date'] = calls_df['call_start_ts'].dt.date
    daily_calls = calls_df.groupby('date').size()
    axes[1, 1].plot(daily_calls.index, daily_calls.values, marker='o')
    axes[1, 1].set_title('Calls per Day')

    plt.tight_layout()
    fig.savefig(os.path.join(RAW_DIR, "cdr_dataset_analysis.png"), dpi=300, bbox_inches='tight')
    plt.close(fig)

if __name__ == "__main__":
    generate_dataset()
