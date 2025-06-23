import threading

import storage

from utils import check_secrets, periodic_messages


threading.Thread(target=periodic_messages, daemon=True).start()

if __name__ == "__main__":
    check_secrets()
    storage.init_db()
    from routes import app
    app.run(host="0.0.0.0", port=5001, debug=True)
