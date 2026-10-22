"""Flask application factory.

Creates and configures the Flask app, initialises the database connection,
registers all route blueprints, and sets up CORS for the React dev server.
"""

import sys
import os

# Ensure the backend directory is on the Python path so that `db`, `helpers`,
# and `routes.*` can be imported regardless of the working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from db import init_db, get_client, get_db
from database import create_indexes
from routes.auth_routes import auth_bp
from routes.state_routes import state_bp
from routes.feedback_routes import feedback_bp
from routes.workspace_routes import workspace_bp
from routes.theme_routes import theme_bp
from routes.feature_routes import feature_bp
from routes.prd_routes import prd_bp
from routes.roadmap_routes import roadmap_bp
from routes.dashboard_routes import dashboard_bp
from routes.preferences_routes import preferences_bp
from routes.chat_routes import chat_bp
from routes.product_routes import product_bp


def create_app(config_override=None):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

    # --- CORS Configuration ---
    # Allow the React development server to communicate with Flask with credentials (cookies/session).
    CORS(
        app,
        supports_credentials=True,
        origins=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:3000",
        ],
    )

    # --- Database Initialisation ---
    print("Initialising MongoDB connection...")
    init_db(app)
    if app.config.get("ENSURE_INDEXES", True):
        create_indexes(get_db())

    # --- Register Blueprints ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(state_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(workspace_bp)
    app.register_blueprint(theme_bp)
    app.register_blueprint(feature_bp)
    app.register_blueprint(prd_bp)
    app.register_blueprint(roadmap_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(preferences_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(product_bp)

    # --- Root and Health check endpoints ---
    @app.route("/", methods=["GET"])
    def index():
        return jsonify({
            "success": True,
            "message": "AI-Driven Product Assistant Backend API is running.",
            "endpoints": "/api/health",
        })

    @app.route("/api/health", methods=["GET"])
    def health():
        try:
            client = get_client()
            if client is None:
                return jsonify({
                    "status": "degraded",
                    "database": "not_initialised",
                    "message": "MongoDB client is not yet initialised.",
                }), 503
            client.admin.command("ping")
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "db_name": app.config.get("MONGO_DB_NAME"),
            }), 200
        except Exception as exc:
            return jsonify({
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(exc),
            }), 503

    # --- Global error handlers ---
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "success": False,
            "data": None,
            "message": getattr(e, "description", "Bad request."),
        }), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "success": False,
            "data": None,
            "message": "The requested endpoint was not found.",
        }), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({
            "success": False,
            "data": None,
            "message": "Internal server error occurred.",
        }), 500

    return app


if __name__ == "__main__":
    application = create_app()
    port = Config.PORT
    print(f"\n=======================================================")
    print(f"  AI-Driven Product Assistant Backend")
    print(f"  Listening on: http://localhost:{port}")
    print(f"  Health Check: http://localhost:{port}/api/health")
    print(f"=======================================================\n")
    application.run(host="0.0.0.0", port=port, debug=Config.DEBUG)
