import random
from collections import defaultdict
from config import Config

config = Config()

class SocialStructure:
    """
    Class to model social structures among users for 
    generating realistic call patterns based on community ties.
    """
    
    def __init__(self, num_users):
        """
        Initialize the SocialStructure with the number of users.
        
        Parameters:
        num_users (int): Total number of users in the social structure.
        """
        self.num_users = num_users
        self.users = []
        self.communities = {}
        self.user_communities = {}
        
    def generate_communities(self):
        """
        Generate realistic social communities including families, 
        work groups, and friend circles.
        
        Returns:
        tuple: A tuple containing the list of users and the communities created.
        """
        # Family communities (dense, strong ties)
        family_communities = []
        for i in range(80):  # 80 families
            size = random.choices([2, 3, 4, 5], weights=[0.2, 0.4, 0.3, 0.1])[0]
            family = [f"user_{j:04d}" for j in range(len(self.users), len(self.users) + size)]
            self.users.extend(family)
            family_communities.append(family)
            
        # Work communities (medium density)
        work_communities = []
        for i in range(30):  # 30 work groups
            size = random.choices([3, 5, 8, 12], weights=[0.3, 0.4, 0.2, 0.1])[0]
            work_group = [f"user_{j:04d}" for j in range(len(self.users), len(self.users) + size)]
            self.users.extend(work_group)
            work_communities.append(work_group)
        
        # Friend circles (loose connections)
        friend_circles = []
        remaining_users = config.NUM_USERS - len(self.users)
        friend_size = 4
        for i in range(0, remaining_users, friend_size):
            friend_group = [f"user_{j:04d}" for j in range(len(self.users), 
                                                         min(len(self.users) + friend_size, config.NUM_USERS))]
            self.users.extend(friend_group)
            if len(friend_group) >= 2:
                friend_circles.append(friend_group)
        
        self.communities = {
            'families': family_communities,
            'work_groups': work_communities,
            'friend_circles': friend_circles
        }
        
        # Map users to their communities
        for user in self.users:
            self.user_communities[user] = []
            
        for comm_type, communities in self.communities.items():
            for comm in communities:
                for user in comm:
                    if user in self.user_communities:
                        self.user_communities[user].append(comm_type)
        
        return self.users, self.communities
    
    def get_community_call_probability(self, user1, user2):
        """
        Calculate the probability of a call between two users 
        based on shared community memberships.
        
        Parameters:
        user1 (str): Identifier of the first user.
        user2 (str): Identifier of the second user.
        
        Returns:
        float: Probability of a call between the two users.
        """
        comm1 = set(self.user_communities.get(user1, []))
        comm2 = set(self.user_communities.get(user2, []))
        
        shared_communities = comm1.intersection(comm2)
        
        if not shared_communities:
            return 0.01  # Low probability for strangers
        
        # Higher probability for family, then work, then friends
        if any('family' in comm for comm in shared_communities):
            return 0.3
        elif any('work' in comm for comm in shared_communities):
            return 0.15
        else:  # friends
            return 0.08