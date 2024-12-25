import os
import cv2
import json
import boto3
import logging
import mimetypes
from flask import Blueprint, request, jsonify, Response

from app.utils import get_pinecone_index, generate_embeddings, crop_faces, convert_video_to_30fps
from app.config import Config


video_bp = Blueprint('video', __name__)
index = get_pinecone_index(Config.PINECONE_API_KEY, Config.PINECONE_VIDEO_INDEX)


@video_bp.route('/search', methods=['POST'])
def verify():
    try:
        if 'image' not in request.files or 'top_k' not in request.form:
            return jsonify({"status": "failed", "error": "Image and top_k are required"}), 400
        
        image_file = request.files['image']
        hex_id = str(os.urandom(4).hex())

        # Check if the file is an image based on its MIME type
        mime_type, _ = mimetypes.guess_type(image_file.filename)
        if not mime_type or not mime_type.startswith('image'):
            return jsonify({"status": "failed", "error": "Invalid file type. Only image files are allowed"}), 400
        
        input_image_path = os.path.join("temp", f"{hex_id}_input_image.jpg")
        os.makedirs("temp", exist_ok=True)
        image_file.save(input_image_path)
        
        # Crop the face from the image
        cropped_face_path = crop_faces(input_image_path)
        logging.info(f"Found {len(cropped_face_path)} faces in the input image")
        if len(cropped_face_path) == 0:
            return jsonify({"status": "failed", "error": "No face detected in the image"}), 400

        top_k = int(request.form['top_k'])
        
        # Query Pinecone for video matches
        query_result_video = index.query(
            namespace="preprocessed-videos",
            vector=generate_embeddings(cropped_face_path[0]),
            top_k=top_k,
            include_metadata=True
        )

        # Query Pinecone for image matches
        query_result_image = index.query(
            namespace="preprocessed-images",
            vector=generate_embeddings(cropped_face_path[0]),
            top_k=top_k,
            include_metadata=True
        )
        
        print(query_result_video)
        print(query_result_image)
        
        
        # Extract and filter matches by score
        video_matches = [
            {
                "id": match["id"],
                "score": match["score"],
                "metadata": match["metadata"]
            }
            for match in query_result_video["matches"] if match["score"] >= 0.5  # Only include matches with score >= 0.7
        ]
        
        image_matches = [
            {
                "id": match["id"],
                "score": match["score"],
                "metadata": match["metadata"]
            }
            for match in query_result_image["matches"] if match["score"] >= 0.5  # Only include matches with score >= 0.7
        ]
        
        # If no matches found above the threshold, respond with "no result found"
        if not video_matches and not image_matches:
            return jsonify({"status": "success", "message": "No result found"}), 200

        formatted_results = {
            "video_matches": video_matches,
            "image_matches": image_matches
        }

        # Format response with indentation using json.dumps
        response = {
            "status": "success",
            "data": formatted_results
        }

        # Return the response with proper formatting
        return Response(
            response=json.dumps(response, indent=2),
            status=200,
            mimetype='application/json'
        )

    except Exception as e:
        logging.error(f"Error during verification: {e}")
        return jsonify({"status": "failed", "error": str(e)}), 500


                    
 # Create an S3 client
s3 = boto3.client('s3')
    
@video_bp.route('/ingest', methods=['POST'])
def ingest_video_image():
    try:
        if 'files' not in request.files:
            return jsonify({"status": "error", "message": "No files provided"}), 400

        files = request.files.getlist('files')
        
        hex_id = str(os.urandom(4).hex())
        upload_directory = f"uploads/{hex_id}/"
        
        ingested_files = []
        s3_links = []
        total_upserts = 0  # Count of all vectors upserted


        for file in files:
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(file.filename)
            if not mime_type or not (mime_type.startswith('image') or mime_type.startswith('video')):
                return jsonify({"status": "error", "message": "Invalid file type. Only image and video files are allowed."}), 400

            # Save the file locally
            upload_path = os.path.join(upload_directory, file.filename)
            os.makedirs(upload_directory, exist_ok=True)
            file.save(upload_path)

            # Find the extension of the file
            ext = os.path.splitext(file.filename)[1][1:]  # Extract extension without the dot

            if mime_type.startswith('image'):
                # Upload the file to S3
                bucket_name = 'trainingdata-public'
                object_name = f'search/original_image/{file.filename}'

                try:
                    s3.upload_file(
                        upload_path,
                        bucket_name,
                        object_name,
                        ExtraArgs={'ContentType': f'image/{ext}'}
                    )
                    logging.info(f"File {file.filename} uploaded successfully to {bucket_name}/{object_name}")
                    image_link = f"https://trainingdata-public.s3.ap-south-1.amazonaws.com/{object_name}"
                    s3_links.append(image_link)
                    
                    # Crop faces from the image
                    cropped_faces = crop_faces(upload_path)
                    
                    file_type = ext
                    file_name_with_extension = os.path.basename(file.filename)  # Get original file name with extension

                    for i, face_path in enumerate(cropped_faces):
                        embeddings = generate_embeddings(face_path)
                        face_count = i + 1  # Use 1-based numbering for face count

                        metadata = {
                            'file_type': file_type,
                            'file_name': file_name_with_extension,
                            'face_no': face_count,
                            'link': image_link
                        }

                        unique_id = f"{file_name_with_extension}#{face_count}"

                        # Create vector for Pinecone
                        vector = {
                            "id": unique_id,
                            "values": embeddings,
                            "metadata": metadata
                        }

                        # Upsert vector to Pinecone
                        index.upsert([vector], namespace="preprocessed-images")
                        total_upserts += 1  # Increment the count of upserts
                        
                    # Add to ingested_files list after successful processing
                    ingested_files.append(file.filename)

                        
                except Exception as e:
                    logging.error(f"Error processing file '{file.filename}': {e}")
                    return jsonify({"status": "error", "message": str(e)}), 500
                
                
            elif mime_type.startswith('video'):
                # Convert the video to 30 FPS and save it
                converted_video_path = os.path.join(upload_directory, f"converted_{file.filename}")
                convert_video_to_30fps(upload_path, converted_video_path)
                
                # Upload the original video to S3
                bucket_name = 'trainingdata-public'
                object_name = f'search/original_videos/{file.filename}'
                
                try:
                    s3.upload_file(
                        upload_path,
                        bucket_name,
                        object_name,
                        ExtraArgs={'ContentType': f'video/mp4'}
                    )
                    logging.info(f"File {file.filename} uploaded successfully to {bucket_name}/{object_name}")
                    video_link = f"https://trainingdata-public.s3.ap-south-1.amazonaws.com/{object_name}"
                    s3_links.append(video_link)

                    
                    cap = cv2.VideoCapture(converted_video_path)
                    frame_count = 0
                    
                    while cap.isOpened():
                        ret, frame = cap.read()
                        if not ret:
                            break

                        if frame_count % 15 == 0:  # Process every 15th frame
                            frame_path = os.path.join(upload_directory, f"frame_{frame_count}.jpg")
                            cv2.imwrite(frame_path, frame)

                            cropped_faces = crop_faces(frame_path)
                            file_name_with_extension = os.path.basename(file.filename)
                            file_type = ext

                            for i, face_path in enumerate(cropped_faces):
                                embeddings = generate_embeddings(face_path)
                                face_count = i + 1
                                time_stamp_sec = frame_count / 30  # Convert frame count to seconds

                                metadata = {
                                    'file_type': file_type,
                                    'file_name': file_name_with_extension,
                                    'time_stamp': time_stamp_sec,
                                    'face_no': face_count,
                                    'link': video_link
                                }

                                unique_id = f"{file_name_with_extension}#{frame_count}_{face_count}"

                                vector = {
                                    "id": unique_id,
                                    "values": embeddings,
                                    "metadata": metadata
                                }

                                index.upsert([vector], namespace="preprocessed-videos")
                                total_upserts += 1  # Increment the count of upserts

                        frame_count += 1

                    cap.release()
                    
                    # Add to ingested_files list after successful processing
                    ingested_files.append(file.filename)

                except Exception as e:
                    logging.error(f"Error processing video file '{file.filename}': {e}")
                    return jsonify({"status": "error", "message": str(e)}), 500
                
                
        response = {
            "status": "success",
            "message": f"{len(ingested_files)} files ingested successfully",
            "data": {
                "ingested_files": ingested_files,
                "s3_links": s3_links,
                "total_upserts": total_upserts
            }
        }

        return jsonify(response), 200

    except Exception as e:
        logging.error(f"Error during ingestion: {e}")
        return jsonify({"status": "failed", "error": str(e)}), 500
