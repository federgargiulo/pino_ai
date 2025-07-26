FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY inference_service.py .
EXPOSE 5000
CMD ["python","inference_service.py","--file","/data/samples.csv"]
