FROM python:3.10.8-slim

# Update packages and install dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y \
    git \
    ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /requirements.txt

# Install Python dependencies
RUN pip3 install -U pip && \
    pip3 install -U -r /requirements.txt

# Create app directory
RUN mkdir /FileToLink
WORKDIR /FileToLink

# Copy project files
COPY . /FileToLink

# Start bot
CMD ["python", "bot.py"]
