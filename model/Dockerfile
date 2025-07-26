FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY inference_service.py /app/inference_service.py
EXPOSE 5000
ENV DATA_DIR=/data/assets WINDOW_S=30 FREQ_HZ=10
CMD ["uvicorn","inference_service:app","--host","0.0.0.0","--port","5000"]
