"""
Configuration module for telecom anomaly detection dataset generation.

This module defines the parameters and distributions used for generating
synthetic Call Detail Records (CDRs) with realistic patterns and anomalies.
"""

import random
import numpy as np
from faker import Faker

# Global dataset parameters
NUM_USERS = 150000
NUM_CELL_TOWERS = 50
DAYS = 7
ANOMALY_RATIO = 0.05  # 5% anomalous calls

class Config:
    """
    Configuration class containing all parameters for CDR dataset generation.
    
    Centralizes configuration to ensure consistency across data generators
    and anomaly detection components.
    """
    
    # Dataset scale parameters
    NUM_USERS = NUM_USERS
    NUM_CELL_TOWERS = NUM_CELL_TOWERS
    DAYS = DAYS
    ANOMALY_RATIO = ANOMALY_RATIO
    
    # Geographic bounds for Delhi region (latitude/longitude)
    # Used for realistic cell tower placement and call patterns
    DELHI_BOUNDS = {
        'lat_min': 28.40, 'lat_max': 28.90,
        'lon_min': 76.80, 'lon_max': 77.40
    }
    
    # Hourly call probability distributions for different user types
    # Values represent relative probability of calls during each hour (0-23)
    TIME_DISTRIBUTIONS = {
        'business': [0.01, 0.005, 0.002, 0.001, 0.003, 0.01, 0.05, 0.12, 0.15, 0.14, 0.13, 0.11,
                    0.09, 0.08, 0.07, 0.06, 0.05, 0.07, 0.12, 0.15, 0.14, 0.11, 0.09, 0.06],
        'social': [0.02, 0.01, 0.005, 0.003, 0.005, 0.02, 0.08, 0.12, 0.10, 0.08, 0.07, 0.06,
                  0.05, 0.04, 0.04, 0.05, 0.07, 0.10, 0.15, 0.18, 0.16, 0.14, 0.12, 0.08]
    }
    
    # Call duration statistics (mean, std deviation, minimum) in seconds
    # Defines normal patterns and anomaly types for call length analysis
    DURATION_DISTRIBUTIONS = {
        'normal': {'mean': 180, 'std': 120, 'min': 10},
        'business': {'mean': 300, 'std': 180, 'min': 30},
        'short_anomaly': {'mean': 3, 'std': 2, 'min': 1},
        'long_anomaly': {'mean': 3600, 'std': 1800, 'min': 1800}
    }

    # Parallelism settings
    # Enable or disable multiprocessing for generation
    ENABLE_PARALLEL = True
    # Number of worker processes; 0 or None means use os.cpu_count()
    NUM_WORKERS = None
    # Generate calls in chunks per worker to reduce overhead
    CALLS_PER_CHUNK = 10000

#config = Config()
fake = Faker('en_IN')
np.random.seed(42)
random.seed(42)