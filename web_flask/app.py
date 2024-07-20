from flask import Flask, Blueprint, render_template
from .auth import auth
from .main import main
from .collection import collection
from .expense import expense
from models import storage
from models.user import User
from flask_login import LoginManager, current_user
from os import getenv
import uuid
import requests

app = Flask(__name__)
app.register_blueprint(auth, url_prefix='/spendsmart')
app.register_blueprint(main, url_prefix='/spendsmart')
app.register_blueprint(collection, url_prefix='/spendsmart')
app.register_blueprint(expense, url_prefix='/spendsmart')
app.secret_key = getenv("SPENDSMART_SECRET_KEY")

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

api_port = getenv("SPENDSMART_API_PORT")
api_host = getenv("SPENDSMART_API_HOST")

@login_manager.user_loader
def load_user(user_id):
    """
    A user loader tells Flask-Login how to find a specific user from the ID that is stored in their session cookie.
    """
    user = storage.get(User, user_id)
    return user

def get_notifications(user_id, params):
    notification_api_url = "http://{}:{}/api/v1/{}/notifications".format(api_host, api_port,
        user_id)
    try:
        notification_response = requests.get(notification_api_url,
                                             params=params)
        notifications = notification_response.json(
        ) if notification_response.status_code == 200 else []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching notifications: {e}")
        notifications = []
    return notifications


@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        params = {'read': False}
        notifications = get_notifications(current_user.id, params=params)
    else:
        notifications = []
    return dict(notifications=notifications)


@app.teardown_appcontext
def close_db(error):
    """ Remove the current SQLAlchemy Session """
    storage.close()


if __name__ == "__main__":
    """ Main Function """
    app.run(host='0.0.0.0', port=5000, debug=True)
