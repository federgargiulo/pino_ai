FROM python:3.11-slim
WORKDIR /app
COPY data_generator.py .
RUN pip install --no-cache-dir pandas numpy
CMD ["python","data_generator.py","--file","/data/samples.csv"]
