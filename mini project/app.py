# app.py
from flask import Flask
from controllers.auth import auth
from controllers.student import student
from controllers.staff import staff

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = SECRET_KEY
    app.register_blueprint(auth)
    app.register_blueprint(student)
    app.register_blueprint(staff)
    return app

if __name__ == "__main__":
    app = create_app()
    # debug True for development only
    app.run(host="0.0.0.0", port=5000, debug=True)

