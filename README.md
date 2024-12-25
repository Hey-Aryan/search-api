# Search API v3.1

## Prerequisites
- Docker with NVIDIA Container Toolkit installed
- AWS credentials in `~/.aws`
- Host directories:
  - `/temp`
  - `/uploads`

## Build the Docker Image
```bash
docker build -t search-api-v3.1 .
```

## Run the Docker Container
```bash
docker run -d \
  --name search-api-v3.1-container \
  -p 5110:5110 \
  --runtime=nvidia \
  --shm-size=20g \
  -v /search-api/temp:/app/temp \
  -v /search-api/uploads:/app/uploads \
  -v /home/user-name/.aws:/root/.aws \
  --restart always \
  search-api-v3.1 python run.py
```

## Verify the Container
- Check running containers:
  ```bash
  docker ps
  ```
- View logs:
  ```bash
  docker logs search-api-v3.1-container
  ```

## Stop & Remove the Container
```bash
docker stop search-api-v3.1-container

docker rm search-api-v3.1-container
```

## API Usage with cURL
1. Audio Search:
Search for top matches for an audio file:

```bash
curl --location 'http://<host-ip>:8050/audio/search' \
--form 'file=@"<path-to-your-audio-file>"' \
--form 'top_k="<number-of-matches>"'
```

2. Video Search:
Search for top matches for an image in a video:
```bash
curl --location 'http://<host-ip>:5110/video/search' \
--form 'image=@"<path-to-your-image-file>"' \
--form 'top_k="<number-of-matches>"'
``` 

3. Audio Ingest:
Ingest an audio file for a specific speaker:
```bash
curl --location 'http://<host-ip>:8050/audio/ingest' \
--form 'speaker="<speaker-name>"' \
--form 'files=@"<path-to-your-audio-file>"'
```

4. Video Ingest:
Ingest a video file:
```bash
curl --location 'http://<host-ip>:5110/video/ingest' \
--form 'files=@"<path-to-your-video-file>"'
```

## Troubleshooting
- **Port conflict**: Check with `sudo netstat -tuln | grep 5110`.
- **GPU issues**: Ensure NVIDIA drivers/toolkit are installed.
- **AWS credentials**: Verify `~/.aws` setup.

For details, refer to Docker/NVIDIA docs or contact the maintainer.
