import random
from datetime import datetime, timedelta
from config import Config

config = Config()



class AnomalyInjector:
    """
    Class to inject various types of call anomalies into a dataset of 
    call records, simulating realistic telecommunication patterns.
    """
    def __init__(self, social_struct, user_profiles, cell_towers, call_gen):
        """
        Initialize the AnomalyInjector with social structure, user profiles, 
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
        self.call_gen = call_gen
        
    def inject_short_calls(self, base_calls, num_anomalies):
        """
        Inject extremely short calls (less than 5 seconds) into the call dataset.
        
        Parameters:
        base_calls (list): The original list of call records.
        num_anomalies (int): Number of short calls to inject.
        
        Returns:
        list: List of injected short call anomalies.
        """
        anomalies = []
        call_id_start = len(base_calls)
        
        for i in range(num_anomalies):
            caller = random.choice(self.user_profiles)['user_id']
            callee = random.choice([u for u in self.user_dict.keys() if u != caller])
            
            # Random day and time
            day = random.randint(0, config.DAYS - 1)
            timestamp = self.call_gen.generate_timestamp(day, 'social')
            duration = random.randint(1, 5)  # 1-5 seconds
            end_time = timestamp + timedelta(seconds=duration)
            
            call_record = {
                'call_id': f"call_{call_id_start + i:06d}",
                'caller_id': caller,
                'callee_id': callee,
                'call_start_ts': timestamp,
                'call_end_ts': end_time,
                'call_duration': duration,
                'first_cell_id': self.user_dict[caller]['home_cell_id'],
                'last_cell_id': self.user_dict[caller]['home_cell_id'],
                'caller_imei': self.user_dict[caller]['imei'],
                'caller_imsi': self.user_dict[caller]['imsi'],
                'callee_imsi': self.user_dict[callee]['imsi'],
                'is_anomaly': 1,
                'anomaly_type': 'short_call'
            }
            
            anomalies.append(call_record)
        
        return anomalies
    
    def inject_long_calls(self, base_calls, num_anomalies):
        """
        Inject extremely long calls (greater than 1 hour) into the call dataset.
        
        Parameters:
        base_calls (list): The original list of call records.
        num_anomalies (int): Number of long calls to inject.
        
        Returns:
        list: List of injected long call anomalies.
        """
        anomalies = []
        call_id_start = len(base_calls) + num_anomalies  # Continue from short calls
        
        for i in range(num_anomalies):
            caller = random.choice(self.user_profiles)['user_id']
            # Long calls more likely with known contacts
            callee = self.call_gen.select_callee(caller)
            
            day = random.randint(0, config.DAYS - 1)
            timestamp = self.call_gen.generate_timestamp(day, 'social')
            duration = random.randint(3600, 7200)  # 1-2 hours
            end_time = timestamp + timedelta(seconds=duration)
            
            call_record = {
                'call_id': f"call_{call_id_start + i:06d}",
                'caller_id': caller,
                'callee_id': callee,
                'call_start_ts': timestamp,
                'call_end_ts': end_time,
                'call_duration': duration,
                'first_cell_id': self.user_dict[caller]['home_cell_id'],
                'last_cell_id': self.user_dict[caller]['home_cell_id'],
                'caller_imei': self.user_dict[caller]['imei'],
                'caller_imsi': self.user_dict[caller]['imsi'],
                'callee_imsi': self.user_dict[callee]['imsi'],
                'is_anomaly': 1,
                'anomaly_type': 'long_call'
            }
            
            anomalies.append(call_record)
        
        return anomalies
    
    def inject_off_hour_calls(self, base_calls, num_anomalies):
        """
        Inject calls that occur during unusual hours (between 2-5 AM) into the dataset.
        
        Parameters:
        base_calls (list): The original list of call records.
        num_anomalies (int): Number of off-hour calls to inject.
        
        Returns:
        list: List of injected off-hour call anomalies.
        """
        anomalies = []
        call_id_start = len(base_calls) + 2 * num_anomalies  # Continue from previous
        
        for i in range(num_anomalies):
            caller = random.choice(self.user_profiles)['user_id']
            callee = random.choice([u for u in self.user_dict.keys() if u != caller])
            
            day = random.randint(0, config.DAYS - 1)
            base_date = datetime(2024, 1, 1) + timedelta(days=day)
            # Off-hours: 2-5 AM
            hour = random.randint(2, 4)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            
            timestamp = base_date.replace(hour=hour, minute=minute, second=second)
            duration = self.call_gen.generate_duration(self.user_dict[caller]['user_type'])
            end_time = timestamp + timedelta(seconds=duration)
            
            call_record = {
                'call_id': f"call_{call_id_start + i:06d}",
                'caller_id': caller,
                'callee_id': callee,
                'call_start_ts': timestamp,
                'call_end_ts': end_time,
                'call_duration': duration,
                'first_cell_id': self.user_dict[caller]['home_cell_id'],
                'last_cell_id': self.user_dict[caller]['home_cell_id'],
                'caller_imei': self.user_dict[caller]['imei'],
                'caller_imsi': self.user_dict[caller]['imsi'],
                'callee_imsi': self.user_dict[callee]['imsi'],
                'is_anomaly': 1,
                'anomaly_type': 'off_hour_call'
            }
            
            anomalies.append(call_record)
        
        return anomalies

    def inject_burst_calls(self, base_calls, num_anomalies):
        """
        Inject burst calling patterns (multiple calls in a short period) into the dataset.
        
        Parameters:
        base_calls (list): The original list of call records.
        num_anomalies (int): Total number of burst calls to inject.
        
        Returns:
        list: List of injected burst call anomalies.
        """
        anomalies = []
        call_id_start = len(base_calls) + 3 * num_anomalies
        
        # Select a few users to be burst callers
        burst_callers = random.sample(self.user_profiles, num_anomalies // 10)
        
        anomaly_count = 0
        for caller_profile in burst_callers:
            caller = caller_profile['user_id']
            day = random.randint(0, config.DAYS - 1)
            base_time = self.call_gen.generate_timestamp(day, 'social')
            
            # Generate 10-20 calls in 1-hour window
            num_calls_in_burst = random.randint(10, 20)
            
            for j in range(num_calls_in_burst):
                if anomaly_count >= num_anomalies:
                    break
                    
                callee = random.choice([u for u in self.user_dict.keys() if u != caller])
                # Random time within 1 hour window
                time_offset = random.randint(0, 3600)
                timestamp = base_time + timedelta(seconds=time_offset)
                duration = random.randint(10, 60)  # Short calls for bursts
                end_time = timestamp + timedelta(seconds=duration)
                
                call_record = {
                    'call_id': f"call_{call_id_start + anomaly_count:06d}",
                    'caller_id': caller,
                    'callee_id': callee,
                    'call_start_ts': timestamp,
                    'call_end_ts': end_time,
                    'call_duration': duration,
                    'first_cell_id': self.user_dict[caller]['home_cell_id'],
                    'last_cell_id': self.user_dict[caller]['home_cell_id'],
                    'caller_imei': caller_profile['imei'],
                    'caller_imsi': caller_profile['imsi'],
                    'callee_imsi': self.user_dict[callee]['imsi'],
                    'is_anomaly': 1,
                    'anomaly_type': 'burst_call'
                }
                
                anomalies.append(call_record)
                anomaly_count += 1
        
        return anomalies