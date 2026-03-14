FROM python:3.11-slim

WORKDIR /opt/project
COPY docker/python-app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
