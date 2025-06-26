import threading

from storage import init_db
from routes import app
from utils import check_secrets, periodic_messages


threading.Thread(target=periodic_messages, daemon=True).start()

check_secrets()
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
