# Minimal mock origin: a Flask app that echoes the inbound
# request as JSON so the walkthrough can show what the proxy
# forwarded. Tiny image; the whole point is "boring upstream".
FROM python:3.12-alpine

WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.* gunicorn==21.*

COPY server.py /app/server.py

EXPOSE 3000
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:3000", "server:app"]
