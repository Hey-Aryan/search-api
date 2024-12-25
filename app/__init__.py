from flask import Flask
from app.audio import audio_bp
from app.video import video_bp

def create_app():
    
    app = Flask(__name__)
    
    app.register_blueprint(audio_bp, url_prefix='/audio')
    app.register_blueprint(video_bp, url_prefix='/video')
    
    return app
