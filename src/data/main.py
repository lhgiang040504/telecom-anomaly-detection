from config import Config
from utils import generate_cell_towers, generate_user_profiles, create_summarise_fig

from generators import CallGenerator, SocialStructure, AnomalyInjector
from schemas import CDRSchema, UserSchema

import random
import matplotlib.pyplot as plt
from datetime import datetime
import json
import pandas as pd
import os
import sys
sys.path.insert(0, os.getcwd())
from faker import Faker
fake = Faker('en_IN')

BASE_DIR = sys.path[0]
RAW_DIR = os.path.join(BASE_DIR, "dataset", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "dataset", "processed")

def generate_dataset(timestamp):
    """
    Generate synthetic CDR dataset with user profiles, 
    social communities, anomalies, and summary plots.
    
    Args:
        output_path (str): where to save the final calls dataset (CSV).
    
    Returns:
        pd.DataFrame: DataFrame of generated call records.
    """

    '''0'''

    # Create folder name based on timestamp
    run_folder = f"cdr_run_{timestamp}"
    raw_run_dir = os.path.join(RAW_DIR, run_folder)
    os.makedirs(raw_run_dir, exist_ok=True)

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
    anomaly_distribution = calls_df[calls_df['is_anomaly'] == 1]['anomaly_type'].value_counts().to_dict()
    print(anomaly_distribution)
    
    '''_4_'''

    # Save main datasets
    calls_df.to_csv(os.path.join(raw_run_dir, "cdr_call_records.csv"), index=False)
    users_df = pd.DataFrame(user_profiles)
    users_df.to_csv(os.path.join(raw_run_dir, "cdr_user_profiles.csv"), index=False)
    pd.DataFrame(cell_towers).to_csv(os.path.join(raw_run_dir, "cdr_cell_towers.csv"), index=False)

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
    pd.DataFrame(community_data).to_csv(os.path.join(raw_run_dir, "cdr_communities.csv"), index=False)

    # Create and save dataset metadata
    dataset_metadata = {
        "dataset_info": {
            "name": "Synthetic CDR Dataset",
            "version": "1.0",
            "description": "Synthetic Call Detail Records dataset for anomaly detection research",
            "generation_date": f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            "run_folder": run_folder
        },
        "generation_parameters": {
            "num_users": Config.NUM_USERS,
            "num_cell_towers": Config.NUM_CELL_TOWERS,
            "days": Config.DAYS,
            "anomaly_ratio": Config.ANOMALY_RATIO,
            "time_period": {
                "start_date": f'{calls_df["call_start_ts"].min().strftime("%Y-%m-%d %H:%M:%S")}',
                "end_date": f'{calls_df["call_start_ts"].max().strftime("%Y-%m-%d %H:%M:%S")}'
            }
        },
        "statistics": {
            "total_calls": f'{len(calls_df)}',
            "normal_calls": f'{len(calls_df[calls_df["is_anomaly"] == 0])}',
            "anomalous_calls": f'{len(calls_df[calls_df["is_anomaly"] == 1])}',
            "anomaly_ratio_actual": f'{len(calls_df[calls_df["is_anomaly"] == 1]) / len(calls_df)}',
            "anomaly_distribution": f'{anomaly_distribution}',
            "unique_callers": f'{calls_df["caller_id"].nunique()}',
            "unique_callees": f'{calls_df["callee_id"].nunique()}',
            "avg_call_duration": f'{calls_df["call_duration"].mean()}',
            "max_call_duration": f'{calls_df["call_duration"].max()}',
            "min_call_duration": f'{calls_df["call_duration"].min()}'
        },
        "files_in_dataset": {
            "cdr_call_records.csv": f"{len(calls_df)} call records",
            "cdr_user_profiles.csv": f"{len(users_df)} user profiles",
            "cdr_cell_towers.csv": f"{len(cell_towers)} cell towers",
            "cdr_communities.csv": f"{len(community_data)} community assignments",
            "cdr_dataset_analysis.png": "Summary visualization"
        }
    }
    # Save metadata as JSON
    metadata_file = os.path.join(raw_run_dir, "dataset_metadata.json")
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(dataset_metadata, f, indent=2, ensure_ascii=False)

    # Also save a simplified README file
    readme_content = f"""# Synthetic CDR Dataset

## Dataset Information
- **Generated on**: {dataset_metadata['dataset_info']['generation_date']}
- **Run Folder**: {run_folder}
- **Total Calls**: {len(calls_df):,}
- **Normal Calls**: {len(calls_df[calls_df['is_anomaly'] == 0]):,}
- **Anomalous Calls**: {len(calls_df[calls_df['is_anomaly'] == 1]):,}
- **Anomaly Ratio**: {dataset_metadata['statistics']['anomaly_ratio_actual']}

## Files
- `cdr_call_records.csv` - Main call records with timestamps and durations
- `cdr_user_profiles.csv` - User demographic information
- `cdr_cell_towers.csv` - Cell tower locations and information  
- `cdr_communities.csv` - Social community assignments
- `cdr_dataset_analysis.png` - Summary visualizations
- `dataset_metadata.json` - Complete dataset metadata

## Anomaly Types
- Short Calls: {anomaly_distribution.get('short_call', 0)} calls
- Long Calls: {anomaly_distribution.get('long_call', 0)} calls
- Off-hour Calls: {anomaly_distribution.get('off_hour', 0)} calls  
- Burst Calls: {anomaly_distribution.get('burst', 0)} calls
"""
    with open(os.path.join(raw_run_dir, "README.md"), 'w', encoding='utf-8') as f:
        f.write(readme_content)

    # Create summarise fig
    create_summarise_fig(calls_df, raw_run_dir)
    
    '''5'''

    # Create aggregated features (export)
    # User-level aggregation
    user_features = []
    
    for user in users_df['user_id']:
        user_calls = calls_df[(calls_df['caller_id'] == user) | (calls_df['callee_id'] == user)]
        caller_calls = calls_df[calls_df['caller_id'] == user]
        
        features = {
            'user_id': user,
            'total_calls': len(user_calls),
            'outgoing_calls': len(caller_calls),
            'incoming_calls': len(user_calls) - len(caller_calls),
            'avg_call_duration': user_calls['call_duration'].mean(),
            'max_call_duration': user_calls['call_duration'].max(),
            'unique_contacts': user_calls['caller_id'].nunique() + user_calls['callee_id'].nunique() - 1,
            'night_calls_ratio': len(user_calls[user_calls['hour'].between(0, 5)]) / len(user_calls),
            'weekend_calls_ratio': len(user_calls[user_calls['call_start_ts'].dt.dayofweek >= 5]) / len(user_calls),
            'short_calls_ratio': len(user_calls[user_calls['call_duration'] < 10]) / len(user_calls),
            'is_anomalous_user': int(user in calls_df[calls_df['is_anomaly'] == 1]['caller_id'].values)
        }
        
        user_features.append(features)

    # Save processed data with run folder name prefix
    processed_filename = f"{run_folder}_cdr_features.csv"
    pd.DataFrame(user_features).to_csv(os.path.join(PROCESSED_DIR, processed_filename), index=False)
    print(f"Dataset generation completed successfully!")
    print(50*'=')
    print(f"Raw data will be saved to: {raw_run_dir}")
    print(f"Processed features saved to: {os.path.join(PROCESSED_DIR, processed_filename)}")

    return None

if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generate_dataset(timestamp)
