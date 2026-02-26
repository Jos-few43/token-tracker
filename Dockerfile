FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY token_dashboard_nexus.py .
EXPOSE 5056
CMD ["python", "token_dashboard_nexus.py"]
