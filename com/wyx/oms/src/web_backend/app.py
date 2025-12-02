from flask import Flask, jsonify
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    app.json.ensure_ascii = False

    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "allow_headers": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        }
    })

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({
            "message": "运维数据分析与管理系统 API",
            "status": "running"
        })

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "healthy"})

    return app
