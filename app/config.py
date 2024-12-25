import os

# Example configuration setup
class Config:
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY","key")
    PINECONE_AUDIO_INDEX = "speaker-recognition"
    PINECONE_VIDEO_INDEX = "face-recognizer"
