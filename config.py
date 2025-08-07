# Golemio Extractor Configuration
API_URL = "https://api.golemio.cz/v2/municipallibraries"
API_KEY = "API_KEY_HERE"  # Replace with your actual API key
OUTPUT_DIR = "data"
TIMEZONE = "Europe/Prague"

# User parameters
DISTRICTS = [
    "praha-1", "praha-2", "praha-3"
]
LATLNG = ["50.124935,14.457204"]
RANGE = [10000]
LIMIT = [5]
OFFSET = [0]
UPDATED_SINCE = ["2019-05-18T07:38:37.000Z"]

# Scheduler settings
SCHEDULED_TIMES = [
    (7, 0)
]

