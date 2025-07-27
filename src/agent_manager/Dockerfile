FROM python:3.10-slim

WORKDIR /workspaces/test100

COPY ./src/agent_manager/requirements.txt ./src/agent_manager/
RUN pip install --no-cache-dir -r ./src/agent_manager/requirements.txt

COPY ./src/shared ./src/shared
COPY ./src/agent_manager/app.py ./src/agent_manager/

WORKDIR /workspaces/test100/src/agent_manager

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
