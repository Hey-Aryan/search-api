import os
import json
import boto3
import logging
import tempfile
import mimetypes
from flask import Blueprint, request, jsonify, Response

from app.utils import get_pinecone_index, convert_audio_to_wav, get_embedding
from app.config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
audio_bp = Blueprint('audio', __name__)
index = get_pinecone_index(Config.PINECONE_API_KEY, Config.PINECONE_AUDIO_INDEX)


@audio_bp.route('/search', methods=['POST'])
def search_audio():
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file provided"}), 400
        
        file = request.files['file']
        
        # Check if the file is an audio file based on its MIME type
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type or not mime_type.startswith('audio'):
            return jsonify({"status": "error", "message": "Invalid file type. Only audio files are allowed."}), 400

        top_k = int(request.form.get('top_k', 3))
        
        # Save the file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            audio_file_path = temp_file.name
        
        try:
            # Convert to WAV and get embedding
            wav_file = convert_audio_to_wav(audio_file_path)
            embedding = get_embedding(wav_file)
            
            # Query Pinecone index
            query_results = index.query(
                namespace="processed-audio",
                vector=embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            os.remove(wav_file)
        finally:
            os.remove(audio_file_path)
        
        # Extract audio matches ensuring serializable format and filter by score
        audio_matches = [
            {
                "speaker": match["metadata"].get("speaker", ""),
                "file_name": match["metadata"].get("file_name", ""),
                "score": match["score"],
                "link": match["metadata"].get("link", "")
            }
            for match in query_results["matches"] if match["score"] * 100 >= 50  # Convert score to percentage and check
        ]

        # If no matches meet the threshold, respond with "no match found"
        if not audio_matches:
            return jsonify({"status": "success", "message": "No match found"}), 200

        response = {
            "status": "success",
            "data": {
                "audio_matches": audio_matches
            }
        }
        
        return Response(
            response=json.dumps(response, indent=2),
            status=200,
            mimetype='application/json'
        )
    
    except Exception as e:
        logging.error(f"Error during audio search: {e}")
        return jsonify({"status": "failed", "error": str(e)}), 500


# Create an S3 client
s3 = boto3.client('s3')

@audio_bp.route('/ingest', methods=['POST'])
def ingest_audio():
    try:
        if 'files' not in request.files or 'speaker' not in request.form:
            return jsonify({"status": "error", "message": "No files provided or speaker name missing"}), 400

        speaker_name = request.form['speaker']
        files = request.files.getlist('files')
       
        hex_id = str(os.urandom(4).hex())
        upload_directory = f"uploads/{hex_id}/"

        ingested_files = []

        for file in files:
            #  Check if the file is an audio file based on its MIME type
            mime_type, _ = mimetypes.guess_type(file.filename)
            if not mime_type or not mime_type.startswith('audio'):
                return jsonify({"status": "error", "message": "Invalid file type. Only audio files are allowed."}), 400
            # Save the file locally
            upload_path = os.path.join(upload_directory, file.filename)
            os.makedirs(upload_directory, exist_ok=True)
            file.save(upload_path)


            # Upload the file to S3
            bucket_name = 'trainingdata-public'
            object_name = f'search/speaker_recoginition/{file.filename}'
            try:
                s3.upload_file(
                    upload_path,
                    bucket_name,
                    object_name,
                    ExtraArgs={'ContentType': 'audio/mp3'}
                )
                logging.info(f"File {file.filename} uploaded successfully to {bucket_name}/{object_name}")

                # Convert to WAV and get embeddings
                wav_file = convert_audio_to_wav(upload_path)
                embedding = get_embedding(wav_file)

                # S3 link for the uploaded file
                link = "https://trainingdata-public.s3.ap-south-1.amazonaws.com/search/speaker_recoginition/"
                
                # Create a unique vector ID
                vector_id = os.path.basename(file.filename).split('.')[0] + "_" + hex_id

                # Metadata for Pinecone
                metadata = {
                    "file_name": file.filename,
                    "id": vector_id,
                    "link": link + file.filename,
                    "speaker": speaker_name
                }

                # Ingest into Pinecone
                index.upsert(
                    vectors=[
                        {
                            "id": vector_id,
                            "values": embedding,
                            "metadata": metadata
                        }
                    ], namespace="processed-audio"
                )

                ingested_files.append({
                    "file_name": file.filename,
                    "link": metadata["link"],
                    "speaker": speaker_name
                })

                os.remove(wav_file)
            except Exception as e:
                logging.error(f"Error processing or uploading file {file.filename}: {e}")
            finally:
                pass
                # Optionally, clean up the local upload file
                #os.remove(upload_path)

        response = {
            "status": "success",
            "message": f"{len(ingested_files)} files ingested successfully",
            "data": ingested_files
        }

        return Response(
            response=json.dumps(response, indent=2),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logging.error(f"Error during audio ingestion: {e}")
        return jsonify({"status": "failed", "error": str(e)}), 500


