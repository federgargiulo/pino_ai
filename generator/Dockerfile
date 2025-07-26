FROM python:3.11-slim
WORKDIR /app
COPY data_generator.py /app/data_generator.py
# Nessuna dipendenza extra necessaria
CMD ["python", "/app/data_generator.py", "--out_dir", "/data/assets", "--freq", "10", "--motors", "4", "--pumps", "2", "--valves", "4", "--window_s", "30"]
