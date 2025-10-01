import random
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from config import Config

config = Config()

def _generate_timestamp(day, call_pattern):
    base_date = datetime(2024, 1, 1) + timedelta(days=day)
    weekday = base_date.weekday()
    if call_pattern == 'business':
        hour_weights = config.TIME_DISTRIBUTIONS['business']
    else:
        hour_weights = config.TIME_DISTRIBUTIONS['social']
    if weekday >= 5:
        if call_pattern == 'business':
            hour_weights = [w * 0.5 for w in config.TIME_DISTRIBUTIONS['business']]
        else:
            hour_weights = [w * 1.5 for w in config.TIME_DISTRIBUTIONS['social']]
    total = sum(hour_weights)
    hour_weights = [w/total for w in hour_weights]
    hour = random.choices(range(24), weights=hour_weights)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return base_date.replace(hour=hour, minute=minute, second=second)

def _generate_duration(user_type, is_anomaly=False, anomaly_type=None):
    if is_anomaly:
        if anomaly_type == 'short_call':
            dist = config.DURATION_DISTRIBUTIONS['short_anomaly']
        else:
            dist = config.DURATION_DISTRIBUTIONS['long_anomaly']
    else:
        if user_type == 'business':
            dist = config.DURATION_DISTRIBUTIONS['business']
        else:
            dist = config.DURATION_DISTRIBUTIONS['normal']
    return max(dist['min'], int(np.random.normal(dist['mean'], dist['std'])))

def _get_community_call_probability(user_communities, user1, user2):
    comm1 = set(user_communities.get(user1, []))
    comm2 = set(user_communities.get(user2, []))
    shared = comm1.intersection(comm2)
    if not shared:
        return 0.01
    if any('family' in c for c in shared):
        return 0.3
    elif any('work' in c for c in shared):
        return 0.15
    return 0.08

def _select_callee(user_ids, user_communities, caller):
    potential_callees = []
    # Use community structure indirectly by scanning communities via user_communities mapping
    # For performance, just sample a subset of users and weight by community probability
    all_users = [u for u in user_ids if u != caller]
    # Prefer a moderate candidate set to keep worker fast
    sample_size = min(500, len(all_users))
    candidates = random.sample(all_users, sample_size) if sample_size < len(all_users) else all_users
    if not candidates:
        return random.choice(user_ids)
    weights = []
    for callee in candidates:
        weights.append(_get_community_call_probability(user_communities, caller, callee))
    if sum(weights) > 0:
        weights = [w/sum(weights) for w in weights]
        return random.choices(candidates, weights=weights)[0]
    return random.choice(candidates)

def _worker_generate_calls(chunk_index, num_calls, total_days, user_profiles, user_communities, cell_towers, seed_base):
    # Ensure independent randomness per worker
    rnd_seed = (seed_base or 1234567) + chunk_index * 9973
    random.seed(rnd_seed)
    np.random.seed(rnd_seed % (2**32 - 1))

    user_dict = {u['user_id']: u for u in user_profiles}
    user_ids = [u['user_id'] for u in user_profiles]
    tower_ids = [t['cell_id'] for t in cell_towers]

    records = []
    for _ in range(num_calls):
        caller = random.choice(user_ids)
        callee = _select_callee(user_ids, user_communities, caller)
        day = random.randint(0, total_days - 1)
        caller_profile = user_dict[caller]
        timestamp = _generate_timestamp(day, caller_profile['call_pattern'])
        duration = _generate_duration(caller_profile['user_type'])
        end_time = timestamp + timedelta(seconds=duration)
        home_cell = caller_profile['home_cell_id']
        first_cell = home_cell
        if random.random() < 0.15:
            last_cell = random.choice([tid for tid in tower_ids if tid != home_cell])
        else:
            last_cell = home_cell
        records.append({
            'caller_id': caller,
            'callee_id': callee,
            'call_start_ts': timestamp,
            'call_end_ts': end_time,
            'call_duration': duration,
            'first_cell_id': first_cell,
            'last_cell_id': last_cell,
            'caller_imei': caller_profile['imei'],
            'caller_imsi': caller_profile['imsi'],
            'callee_imsi': user_dict[callee]['imsi'],
            'is_anomaly': 0,
            'anomaly_type': 'normal'
        })
    return records

class CallGenerator:
    """
    Class to generate synthetic call records based on user social structures,
    call patterns, and durations. It simulates realistic telecommunication activities.
    """
    def __init__(self, social_struct, user_profiles, cell_towers):
        """
        Initialize the CallGenerator with social structure, user profiles, 
        and cell tower information.
        
        Parameters:
        social_struct (SocialStructure): The social structure model.
        user_profiles (list): List of user profiles with relevant details.
        cell_towers (list): List of cell tower information for call records.
        """
        self.social_struct = social_struct
        self.user_profiles = user_profiles
        self.cell_towers = cell_towers
        self.user_dict = {u['user_id']: u for u in user_profiles}

    def generate_timestamp(self, day, call_pattern):
        """
        Generate a realistic timestamp for a call based on the specified 
        call pattern and whether it falls on a weekday or weekend.
        
        Parameters:
        day (int): Day of the simulation (0-6).
        call_pattern (str): Type of call pattern ('business' or 'social').
        
        Returns:
        datetime: Generated timestamp for the call.
        """
        base_date = datetime(2024, 1, 1) + timedelta(days=day)
        weekday = base_date.weekday()  # 0=Mon, ..., 6=Sun
        
        # Choose base distribution
        if call_pattern == 'business':
            hour_weights = config.TIME_DISTRIBUTIONS['business']
        else:
            hour_weights = config.TIME_DISTRIBUTIONS['social']
        
        # Adjust for weekends
        if weekday >= 5:  # Saturday (5) or Sunday (6)
            if call_pattern == 'business':
                hour_weights = [w * 0.5 for w in config.TIME_DISTRIBUTIONS['business']]
            else:
                hour_weights = [w * 1.5 for w in config.TIME_DISTRIBUTIONS['social']]
        
        total = sum(hour_weights)
        hour_weights = [w/total for w in hour_weights]
        
        # Sample hour with updated weights
        hour = random.choices(range(24), weights=hour_weights)[0]
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        
        timestamp = base_date.replace(hour=hour, minute=minute, second=second)
        return timestamp

    def generate_duration(self, user_type, is_anomaly=False, anomaly_type=None):
        """
        Generate a call duration based on user type and whether the call 
        is an anomaly.
        
        Parameters:
        user_type (str): Type of the user ('business' or 'normal').
        is_anomaly (bool): Indicates if the call is an anomaly.
        anomaly_type (str): Type of anomaly ('short_call' or 'long_call').
        
        Returns:
        int: Duration of the call in seconds.
        """
        if is_anomaly:
            if anomaly_type == 'short_call':
                dist = config.DURATION_DISTRIBUTIONS['short_anomaly']
            else:  # long_call
                dist = config.DURATION_DISTRIBUTIONS['long_anomaly']
        else:
            if user_type == 'business':
                dist = config.DURATION_DISTRIBUTIONS['business']
            else:
                dist = config.DURATION_DISTRIBUTIONS['normal']
        
        duration = max(dist['min'], int(np.random.normal(dist['mean'], dist['std'])))
        '''
        duration = int(np.random.lognormal(mean=2.0, sigma=0.5))
        '''
        return duration

    def select_callee(self, caller):
        """
        Select a callee for the caller based on social structures and 
        community memberships.
        
        Parameters:
        caller (str): Identifier of the caller.
        
        Returns:
        str: Identifier of the selected callee.
        """
        # First, try community members (higher probability)
        caller_communities = self.social_struct.user_communities.get(caller, [])
        potential_callees = []
        
        for comm_type, communities in self.social_struct.communities.items():
            for comm in communities:
                if caller in comm:
                    potential_callees.extend([u for u in comm if u != caller])
        
        # Add some random users (weak ties)
        all_users = list(self.user_dict.keys())
        weak_ties = random.sample([u for u in all_users if u != caller], 
                                 min(50, len(all_users) // 20))
        potential_callees.extend(weak_ties)
        
        if not potential_callees:
            potential_callees = [u for u in all_users if u != caller]
        
        # Weight by community probability
        weights = []
        for callee in potential_callees:
            prob = self.social_struct.get_community_call_probability(caller, callee)
            weights.append(prob)
        
        # Normalize weights
        if sum(weights) > 0:
            weights = [w/sum(weights) for w in weights]
            callee = random.choices(potential_callees, weights=weights)[0]
        else:
            callee = random.choice(potential_callees)
            
        return callee

    def generate_normal_calls(self, total_days):
        """
        Generate normal call records over a specified number of days.
        
        Parameters:
        total_days (int): Total number of days to generate calls for.
        
        Returns:
        list: List of generated call records.
        """
        calls = []
        # Estimate calls per day (15-25 per user)
        calls_per_user_per_day = random.randint(15, 25)
        total_normal_calls = int(len(self.user_profiles) * calls_per_user_per_day * total_days * (1 - config.ANOMALY_RATIO))
        print(f"Generating {total_normal_calls} normal calls...")

        if getattr(config, 'ENABLE_PARALLEL', False):
            try:
                workers = getattr(config, 'NUM_WORKERS', None) or os.cpu_count() or 1
                chunk = max(1, getattr(config, 'CALLS_PER_CHUNK', 10000))
                num_chunks = (total_normal_calls + chunk - 1) // chunk
                user_communities = self.social_struct.user_communities
                seed_base = 987654
                with ProcessPoolExecutor(max_workers=workers) as pool:
                    futures = []
                    for idx in range(num_chunks):
                        n = chunk if (idx + 1) * chunk <= total_normal_calls else (total_normal_calls - idx * chunk)
                        futures.append(pool.submit(
                            _worker_generate_calls,
                            idx,
                            n,
                            total_days,
                            self.user_profiles,
                            user_communities,
                            self.cell_towers,
                            seed_base
                        ))
                    accumulated = 0
                    for fut in as_completed(futures):
                        part = fut.result()
                        calls.extend(part)
                        accumulated += len(part)
                        if accumulated % 10000 == 0:
                            print(f"Generated {accumulated} calls...")
                # Assign sequential call_ids after merge
                for i, rec in enumerate(calls):
                    rec['call_id'] = f"call_{i:06d}"
                return calls
            except Exception as e:
                print(f"Parallel generation failed ({e}). Falling back to serial generation.")

        # Serial fallback
        call_id = 0
        for _ in range(total_normal_calls):
            caller = random.choice(self.user_profiles)['user_id']
            callee = self.select_callee(caller)
            day = random.randint(0, total_days - 1)
            caller_profile = self.user_dict[caller]
            timestamp = self.generate_timestamp(day, caller_profile['call_pattern'])
            duration = self.generate_duration(caller_profile['user_type'])
            end_time = timestamp + timedelta(seconds=duration)
            home_cell = caller_profile['home_cell_id']
            first_cell = home_cell
            if random.random() < 0.15:
                last_cell = random.choice([t['cell_id'] for t in self.cell_towers if t['cell_id'] != home_cell])
            else:
                last_cell = home_cell
            calls.append({
                'call_id': f"call_{call_id:06d}",
                'caller_id': caller,
                'callee_id': callee,
                'call_start_ts': timestamp,
                'call_end_ts': end_time,
                'call_duration': duration,
                'first_cell_id': first_cell,
                'last_cell_id': last_cell,
                'caller_imei': caller_profile['imei'],
                'caller_imsi': caller_profile['imsi'],
                'callee_imsi': self.user_dict[callee]['imsi'],
                'is_anomaly': 0,
                'anomaly_type': 'normal'
            })
            call_id += 1
            if call_id % 10000 == 0:
                print(f"Generated {call_id} calls...")
        return calls