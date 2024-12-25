# Search API v3.1

This document provides instructions to build and run the Search API v3.1 Docker container.

## Prerequisites

- Docker installed on your system
- NVIDIA drivers and the NVIDIA Container Toolkit for GPU support
- AWS credentials configured locally under `~/.aws`
- Required host directories:
  - `/temp`
  - `/uploads`

## Build the Docker Image

To build the Docker image, run the following command:

```bash
docker build -t search-api-v3.1 .
```

This command creates a Docker image named `search-api-v3.1` from the `Dockerfile` located in the current directory.

## Run the Docker Container

To run the container, use the following command:

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

### Explanation of the Command

- `-d`: Runs the container in detached mode (in the background).
- `--name search-api-v3.1-container`: Assigns the name `search-api-v3.1-container` to the running container.
- `-p 5110:5110`: Maps port `5110` of the host to port `5110` of the container.
- `--runtime=nvidia`: Specifies that the container should use the NVIDIA runtime for GPU support.
- `--shm-size=20g`: Allocates 20GB of shared memory to the container, useful for memory-intensive operations.
- `-v`: Mounts the following host directories to the container:
  - `/data/Aryan/pi-scout-search-api/temp` -> `/app/temp`
  - `/data/Aryan/pi-scout-search-api/uploads` -> `/app/uploads`
  - `/home/ubuntu/.aws` -> `/root/.aws`
- `--restart always`: Ensures the container restarts automatically if it stops unexpectedly.
- `search-api-v3.1`: Specifies the Docker image to use.
- `python run.py`: Runs the application inside the container.

## Verifying the Container

Once the container is running, you can verify it using the following commands:

### Check the Running Container
```bash
docker ps
```

### View Container Logs
```bash
docker logs search-api-v3.1-container
```

### Access the Application
The application is accessible at `http://<host-ip>:5110`.

## Stopping the Container

To stop the container, use:

```bash
docker stop search-api-v3.1-container
```

To remove the container after stopping:

```bash
docker rm search-api-v3.1-container
```

## Updating the Container

If you make changes to the application, rebuild the image and restart the container:

```bash
docker build -t search-api-v3.1 .
docker stop search-api-v3.1-container
docker rm search-api-v3.1-container
```

Then re-run the container using the command mentioned above.

## Troubleshooting

1. **Port Already in Use**:
   Ensure that port `5110` is not being used by another process. You can check running processes with:
   ```bash
   sudo netstat -tuln | grep 5110
   ```

2. **GPU Issues**:
   Ensure that NVIDIA drivers and the NVIDIA Container Toolkit are properly installed on your system.

3. **AWS Credentials**:
   Verify that your AWS credentials are correctly configured in `~/.aws` on the host system.

For further assistance, please refer to the Docker and NVIDIA documentation or contact the application maintainer.
