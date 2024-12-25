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

## Troubleshooting
- **Port conflict**: Check with `sudo netstat -tuln | grep 5110`.
- **GPU issues**: Ensure NVIDIA drivers/toolkit are installed.
- **AWS credentials**: Verify `~/.aws` setup.

For details, refer to Docker/NVIDIA docs or contact the maintainer.
