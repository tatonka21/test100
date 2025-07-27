FROM python:3.10-slim

WORKDIR /workspaces/test100

COPY ./src/api_gateway/requirements.txt ./src/api_gateway/
RUN pip install --no-cache-dir -r ./src/api_gateway/requirements.txt

COPY ./src/shared ./src/shared
COPY ./src/api_gateway/app.py ./src/api_gateway/

WORKDIR /workspaces/test100/src/api_gateway

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
