# mqtt broker
BROKER_HOST = "10.3.141.177"
BROKER_PORT = 1883

# database
DATABASE_HOST = "localhost"
DATABASE_PORT = 27017

# specifics
AUTONOMY_SLEEP = 60 * 5
DISALLOWED_KEYS = ["time", "status", "topic"]  # limit payload bandwidth
