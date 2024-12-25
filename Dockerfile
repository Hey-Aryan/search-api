# Use Python 3.10-slim as the base image
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libsndfile1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    ffmpeg \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --upgrade pip setuptools wheel
RUN pip install Cython packaging
RUN pip install nemo-toolkit[all]==2.0.0rc1
RUN pip install -r requirements.txt

EXPOSE 5110

CMD ["python", "run.py"]
