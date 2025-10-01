import random
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from faker import Faker
fake = Faker('en_IN')

def generate_cell_towers(num_towers):
    """
    Generate realistic cell tower locations in Delhi.
    
    Parameters:
    num_towers (int): Number of cell towers to generate.
    
    Returns:
    list: List of dictionaries containing cell tower details.
    """
    towers = []
    
    # Area types with different densities
    area_types = [
        {'type': 'downtown', 'weight': 0.3, 'lat_range': (28.61, 28.68), 'lon_range': (77.20, 77.25)},
        {'type': 'commercial', 'weight': 0.25, 'lat_range': (28.55, 28.65), 'lon_range': (77.15, 77.30)},
        {'type': 'residential', 'weight': 0.25, 'lat_range': (28.45, 28.60), 'lon_range': (77.10, 77.35)},
        {'type': 'suburban', 'weight': 0.2, 'lat_range': (28.40, 28.50), 'lon_range': (76.90, 77.40)}
    ]
    
    for i in range(num_towers):
        area = random.choices(area_types, weights=[a['weight'] for a in area_types])[0]
        lat = round(random.uniform(*area['lat_range']), 6)
        lon = round(random.uniform(*area['lon_range']), 6)
        
        tower = {
            'cell_id': f"cell_{i:03d}",
            'latitude': lat,
            'longitude': lon,
            'area_type': area['type'],
            'tower_type': random.choice(['macro', 'macro', 'macro', 'small_cell'])
        }
        towers.append(tower)
    
    return towers

def generate_imei():
    """
    Generate a valid IMEI number using the Luhn algorithm.
    
    Returns:
    str: A valid 15-digit IMEI number as a string.
    """
    imei = [random.randint(0, 9) for _ in range(14)]
    def luhn_residue(digits):
        return sum(sum(divmod(int(d)*(1 + i%2), 10)) for i,d in enumerate(digits[::-1])) % 10
    check_digit = (10 - luhn_residue(imei)) % 10
    imei.append(check_digit)
    return "".join(map(str, imei))


def generate_user_profiles(users, user_home_cells):
    """
    Generate detailed user profiles for a list of users.
    
    Parameters:
    users (list): List of user identifiers.
    user_home_cells (dict): Mapping of users to their home cell IDs.
    
    Returns:
    list: List of dictionaries containing user profile details.
    """
    user_profiles = []
    
    for user in users:
        home_cell = user_home_cells[user]
        
        profile = {
            'user_id': user,
            'phone_number': f"+91{fake.msisdn()[3:]}",  # Indian format
            'imei': generate_imei(), #fake.imei(),
            'imsi': f"405{random.randint(10, 99)}{fake.numerify(text='##########')}",
            'home_cell_id': home_cell,
            'user_type': random.choices(['individual', 'business', 'student'], 
                                      weights=[0.7, 0.2, 0.1])[0],
            'creation_date': fake.date_between(start_date='-2y', end_date='-1m'),
            'call_pattern': random.choices(['business', 'social'], weights=[0.4, 0.6])[0]
        }
        user_profiles.append(profile)
    
    return user_profiles

def create_summarise_fig(calls_df, raw_run_dir):
    # Set the default style for the plots
    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # Extract the hour from the call start timestamps
    # Plot 1
    calls_df['hour'] = calls_df['call_start_ts'].dt.hour
    axes[0, 0].bar(calls_df['hour'].value_counts().index, calls_df['hour'].value_counts().values, alpha=0.7, color='skyblue')
    axes[0, 0].set_title('Call Distribution by Hour')

    # Define bins and labels for call duration distribution
    # Plot 2
    duration_bins = [0, 30, 60, 180, 600, 1800, 3600, calls_df['call_duration'].max()]
    duration_labels = ['<30s', '30-60s', '1-3m', '3-10m', '10-30m', '30-60m', '>1h']
    duration_dist = pd.cut(calls_df['call_duration'], bins=duration_bins, labels=duration_labels).value_counts()
    axes[0, 1].pie(duration_dist.values, labels=duration_dist.index, autopct='%1.1f%%')
    axes[0, 1].set_title('Call Duration Distribution')
    # Plot 3
    anomaly_counts = calls_df[calls_df['is_anomaly'] == 1]['anomaly_type'].value_counts()
    axes[1, 0].bar(anomaly_counts.index, anomaly_counts.values, color='salmon')
    axes[1, 0].set_title('Anomaly Type Distribution')

    # Prepare data for daily call counts
    # Plot 4
    calls_df['date'] = calls_df['call_start_ts'].dt.date
    daily_calls = calls_df.groupby('date').size()
    axes[1, 1].plot(daily_calls.index, daily_calls.values, marker='o')
    axes[1, 1].set_title('Calls per Day')

    plt.tight_layout()
    fig.savefig(os.path.join(raw_run_dir, "cdr_dataset_analysis.png"), dpi=300, bbox_inches='tight')
    plt.close(fig)

def convert_to_serializable(obj):
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.tolist()  # Chuyển đổi thành danh sách
    elif isinstance(obj, (np.integer, np.float)):
        return int(obj) if isinstance(obj, np.integer) else float(obj)  # Chuyển đổi số kiểu numpy
    return obj