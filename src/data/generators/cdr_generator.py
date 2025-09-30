import random
import numpy as np
from datetime import datetime, timedelta
from config import Config

config = Config()

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
        call_id = 0
        
        # Estimate calls per day (15-25 per user)
        calls_per_user_per_day = random.randint(15, 25)
        total_normal_calls = int(len(self.user_profiles) * calls_per_user_per_day * total_days * (1 - config.ANOMALY_RATIO))
        
        print(f"Generating {total_normal_calls} normal calls...")
        
        for _ in range(total_normal_calls):
            caller = random.choice(self.user_profiles)['user_id']
            callee = self.select_callee(caller)
            
            day = random.randint(0, total_days - 1)

            caller_profile = self.user_dict[caller]
            
            timestamp = self.generate_timestamp(day, caller_profile['call_pattern'])
            duration = self.generate_duration(caller_profile['user_type'])
            end_time = timestamp + timedelta(seconds=duration)
            
            # Cell selection (85% same cell, 15% movement)
            home_cell = caller_profile['home_cell_id']
            first_cell = home_cell
            if random.random() < 0.15:
                last_cell = random.choice([t['cell_id'] for t in self.cell_towers if t['cell_id'] != home_cell])
            else:
                last_cell = home_cell
            
            call_record = {
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
            }
            
            calls.append(call_record)
            call_id += 1
            
            if call_id % 10000 == 0:
                print(f"Generated {call_id} calls...")
        
        return calls