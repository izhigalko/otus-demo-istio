FROM python:3.7-slim

EXPOSE 8080
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app.py

CMD ["python", "/app.py"]
