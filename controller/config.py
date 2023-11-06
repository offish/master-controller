# mqtt broker
BROKER_HOST = "192.168.1.5"
BROKER_PORT = 1883

# database
DATABASE_HOST = "localhost"
DATABASE_PORT = 27017

# specifics
AUTONOMY_SLEEP = 1
DISALLOWED_KEYS = ["time", "status", "topic"]  # limit payload bandwidth
