FROM apache/superset:4.1.1

USER root
COPY docker/superset/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
USER superset
