FROM python:3.10-slim

WORKDIR /workspaces/test100

COPY ./src/agent_runtime/requirements.txt ./src/agent_runtime/
RUN pip install --no-cache-dir -r ./src/agent_runtime/requirements.txt

COPY ./src/shared ./src/shared
COPY ./src/agent_runtime/app.py ./src/agent_runtime/

WORKDIR /workspaces/test100/src/agent_runtime

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
