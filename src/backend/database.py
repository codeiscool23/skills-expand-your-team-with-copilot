"""
MongoDB database configuration and setup for Mergington High School API
"""

from pymongo import MongoClient
from argon2 import PasswordHasher

# Try to connect to MongoDB, fall back to in-memory if not available
try:
    client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=1000)
    # Test connection
    client.admin.command('ping')
    db = client['mergington_high']
    activities_collection = db['activities']
    teachers_collection = db['teachers']
    MONGODB_AVAILABLE = True
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"⚠️  MongoDB not available, using in-memory storage: {e}")
    MONGODB_AVAILABLE = False
    # Use dictionaries as in-memory storage
    _in_memory_activities = {}
    _in_memory_teachers = {}
    
    # Create mock collection objects that work with dictionaries
    class MockCollection:
        def __init__(self, storage_dict):
            self.storage = storage_dict
        
        def count_documents(self, query):
            return len(self.storage)
        
        def insert_one(self, document):
            doc_id = document["_id"]
            self.storage[doc_id] = document
        
        def find_one(self, query):
            if not query:
                return None
            doc_id = query.get("_id")
            return self.storage.get(doc_id)
        
        def find(self, query=None):
            if not query:
                # Return copies with _id field added
                results = []
                for key, doc in self.storage.items():
                    result_doc = dict(doc)
                    result_doc['_id'] = key
                    results.append(result_doc)
                return results
            
            results = []
            for key, doc in self.storage.items():
                matches = True
                for condition_key, condition in query.items():
                    if condition_key == "schedule_details.days":
                        # Handle MongoDB $in operator for days
                        if "$in" in condition:
                            target_days = condition["$in"]
                            doc_days = doc.get("schedule_details", {}).get("days", [])
                            if not any(day in doc_days for day in target_days):
                                matches = False
                                break
                    elif condition_key == "schedule_details.start_time":
                        # Handle MongoDB $gte operator
                        if "$gte" in condition:
                            doc_start = doc.get("schedule_details", {}).get("start_time", "00:00")
                            if doc_start < condition["$gte"]:
                                matches = False
                                break
                    elif condition_key == "schedule_details.end_time":
                        # Handle MongoDB $lte operator
                        if "$lte" in condition:
                            doc_end = doc.get("schedule_details", {}).get("end_time", "23:59")
                            if doc_end > condition["$lte"]:
                                matches = False
                                break
                
                if matches:
                    result_doc = dict(doc)
                    result_doc['_id'] = key
                    results.append(result_doc)
            
            return results
        
        def aggregate(self, pipeline):
            # Simple aggregation for days endpoint
            days = set()
            for doc in self.storage.values():
                schedule_days = doc.get("schedule_details", {}).get("days", [])
                days.update(schedule_days)
            
            return [{"_id": day} for day in sorted(days)]
        
        def update_one(self, query, update):
            doc_id = query.get("_id")
            if doc_id in self.storage:
                if "$set" in update:
                    self.storage[doc_id].update(update["$set"])
                elif "$push" in update:
                    for field, value in update["$push"].items():
                        if field not in self.storage[doc_id]:
                            self.storage[doc_id][field] = []
                        self.storage[doc_id][field].append(value)
                elif "$pull" in update:
                    for field, value in update["$pull"].items():
                        if field in self.storage[doc_id]:
                            try:
                                self.storage[doc_id][field].remove(value)
                            except ValueError:
                                pass
                return type('MockResult', (), {'modified_count': 1})()
            return type('MockResult', (), {'modified_count': 0})()
    
    activities_collection = MockCollection(_in_memory_activities)
    teachers_collection = MockCollection(_in_memory_teachers)

# Methods
def hash_password(password):
    """Hash password using Argon2"""
    ph = PasswordHasher()
    return ph.hash(password)

def init_database():
    """Initialize database if empty"""

    # Initialize activities if empty
    if activities_collection.count_documents({}) == 0:
        for name, details in initial_activities.items():
            activities_collection.insert_one({"_id": name, **details})
            
    # Initialize teacher accounts if empty
    if teachers_collection.count_documents({}) == 0:
        for teacher in initial_teachers:
            teachers_collection.insert_one({"_id": teacher["username"], **teacher})

# Initial database if empty
initial_activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Mondays and Fridays, 3:15 PM - 4:45 PM",
        "schedule_details": {
            "days": ["Monday", "Friday"],
            "start_time": "15:15",
            "end_time": "16:45"
        },
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 7:00 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "07:00",
            "end_time": "08:00"
        },
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Morning Fitness": {
        "description": "Early morning physical training and exercises",
        "schedule": "Mondays, Wednesdays, Fridays, 6:30 AM - 7:45 AM",
        "schedule_details": {
            "days": ["Monday", "Wednesday", "Friday"],
            "start_time": "06:30",
            "end_time": "07:45"
        },
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and compete in basketball tournaments",
        "schedule": "Wednesdays and Fridays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Wednesday", "Friday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore various art techniques and create masterpieces",
        "schedule": "Thursdays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Thursday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Monday", "Wednesday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and prepare for math competitions",
        "schedule": "Tuesdays, 7:15 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday"],
            "start_time": "07:15",
            "end_time": "08:00"
        },
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Friday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "amelia@mergington.edu"]
    },
    "Weekend Robotics Workshop": {
        "description": "Build and program robots in our state-of-the-art workshop",
        "schedule": "Saturdays, 10:00 AM - 2:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "10:00",
            "end_time": "14:00"
        },
        "max_participants": 15,
        "participants": ["ethan@mergington.edu", "oliver@mergington.edu"]
    },
    "Science Olympiad": {
        "description": "Weekend science competition preparation for regional and state events",
        "schedule": "Saturdays, 1:00 PM - 4:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "13:00",
            "end_time": "16:00"
        },
        "max_participants": 18,
        "participants": ["isabella@mergington.edu", "lucas@mergington.edu"]
    },
    "Sunday Chess Tournament": {
        "description": "Weekly tournament for serious chess players with rankings",
        "schedule": "Sundays, 2:00 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Sunday"],
            "start_time": "14:00",
            "end_time": "17:00"
        },
        "max_participants": 16,
        "participants": ["william@mergington.edu", "jacob@mergington.edu"]
    },
    "Manga Maniacs": {
        "description": "Explore the fantastic stories of the most interesting characters from Japanese Manga (graphic novels).",
        "schedule": "Tuesdays, 7:00 PM - 8:30 PM",
        "schedule_details": {
            "days": ["Tuesday"],
            "start_time": "19:00",
            "end_time": "20:30"
        },
        "max_participants": 15,
        "participants": []
    }
}

initial_teachers = [
    {
        "username": "mrodriguez",
        "display_name": "Ms. Rodriguez",
        "password": hash_password("art123"),
        "role": "teacher"
     },
    {
        "username": "mchen",
        "display_name": "Mr. Chen",
        "password": hash_password("chess456"),
        "role": "teacher"
    },
    {
        "username": "principal",
        "display_name": "Principal Martinez",
        "password": hash_password("admin789"),
        "role": "admin"
    }
]

