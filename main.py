import threading

from storage import init_db
from routes import app
from dashboard import dashboard
from config import check_config
from utils import periodic_messages


# Validate before anything starts up, so a misconfigured bot fails at boot
# rather than halfway through its first scheduled post.
check_config()
init_db()

app.register_blueprint(dashboard)
app.secret_key = __import__("secrets").token_urlsafe(32)

# One scheduler per process. Gunicorn must therefore run a single worker —
# see the Dockerfile — or every worker posts its own copy to the group.
threading.Thread(target=periodic_messages, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
