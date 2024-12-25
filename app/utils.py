import os
import cv2
import uuid

import json
import torch

import ffmpeg
import logging
import mimetypes

import tempfile
from PIL import Image

from deepface import DeepFace

from datetime import timedelta


from facenet_pytorch import MTCNN
import nemo.collections.asr as nemo_asr

from pinecone.grpc import PineconeGRPC as Pinecone


from app.config import Config



# Initialize MTCNN for face detection
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
mtcnn = MTCNN(keep_all=True, device=device)


# -------------------------------------------------- Pinecone Utility--------------------------------------------------

def get_pinecone_index(api_key, index_name):
    try:
        pc = Pinecone(api_key=api_key)
        return pc.Index(index_name)
    except Exception as e:
        logging.error(f"Error initializing Pinecone index '{index_name}': {e}")
        return None


# -------------------------------------------------- Audio Utility --------------------------------------------------
""" 
#------------------ pudub implementation -------------------

def convert_audio_to_wav(file_path, target_sample_rate=16000):
    audio = AudioSegment.from_file(file_path)
    audio = audio.set_frame_rate(target_sample_rate).set_channels(1)
    temp_wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    audio.export(temp_wav_path, format="wav")
    return temp_wav_path
"""

def get_embedding(wav):
    speaker_model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained("nvidia/speakerverification_en_titanet_large")
    emb = speaker_model.get_embedding(wav)
    return emb.cpu().squeeze().tolist()


def convert_audio_to_wav(file_path, target_sample_rate=16000):
    temp_wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

    try:
        # Attempt to convert the file using ffmpeg
        ffmpeg.input(file_path).output(
            temp_wav_path, ar=target_sample_rate, ac=1, format='wav'
        ).run(quiet=True, overwrite_output=True)
        return temp_wav_path
    except ffmpeg.Error as e:
        print(f"Error during conversion: {e.stderr.decode()}")
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
        raise Exception("Audio conversion failed. Please check the input format.")


# ---------------------------------- Video Utility -----------------------------------------------------------------

def generate_embeddings(image_path):
    """Generates Embeddings from deepface library"""
    try:
        embedding_objs = DeepFace.represent(
            img_path=image_path,
            model_name="VGG-Face",
            detector_backend="skip",
            enforce_detection=False,
            align=False,
            expand_percentage=0,
            normalization="raw"
        )
        return embedding_objs[0]["embedding"]
    except Exception as e:
        logging.error(f"Error generating embedding for image '{image_path}': {e}")
        return None
    
    
    
def crop_faces(image_path):
    """Detects and crops all faces from the image using MTCNN."""
    try:
        image = Image.open(image_path)
        
        # Convert the image to RGB format to ensure compatibility
        image = image.convert('RGB')
        
        # Detect faces in the image
        boxes, probs = mtcnn.detect(image)

        cropped_images_paths = []

        if boxes is not None and len(boxes) > 0:
            # Iterate over all detected faces and crop them
            for i, box in enumerate(boxes):
                cropped_image = image.crop((box[0], box[1], box[2], box[3]))

                # Generate a unique name for each cropped image
                unique_id = uuid.uuid4()
                cropped_image_path = os.path.join("temp", f"cropped_face_{unique_id}.jpg")
                
                # Save each cropped image
                cropped_image.save(cropped_image_path)
                cropped_images_paths.append(cropped_image_path)

            return cropped_images_paths
        else:
            logging.warning("No faces detected in the image.")
            return []
    except Exception as e:
        logging.error(f"Error during face cropping: {e}")
        return []
    
    
    
def convert_video_to_30fps(input_path, output_path):
    """Converts video files into 30fps"""
    try:
        # Open the video file
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception(f"Cannot open video file: {input_path}")

        # Get video properties
        original_fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4

        # Create VideoWriter object for output video at 30 FPS
        out = cv2.VideoWriter(output_path, fourcc, 30, (width, height))

        # Read and write frames to the output file
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)

        # Release resources
        cap.release()
        out.release()

        logging.info(f"Video converted to 30 FPS and saved at: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error converting video to 30 FPS: {e}")
        return None

