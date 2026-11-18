# ruleid: hardcoded-secret
DB_PASSWORD = "Pz8r4kLq9wX2mN7vB3c"
# ruleid: hardcoded-secret
client = connect(host="db", api_key="k4Jd9sLq2Wm8Xp3Rz7Nb")
# ok: hardcoded-secret
DB_PASSWORD = os.environ["DB_PASSWORD"]
# ok: hardcoded-secret
TOKEN_URL = "https://login.example.org/token/v2"
# ok: hardcoded-secret
SECRET_NAME = "prod/app/db"
