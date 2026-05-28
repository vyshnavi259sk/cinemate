FROM python:3.12-slim
WORKDIR /app
RUN pip install flask flask-cors boto3 gunicorn
COPY app.py .
EXPOSE 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "2", "app:app"]
