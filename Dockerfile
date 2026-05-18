FROM python:3.11

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

RUN python -m playwright install --with-deps

CMD ["uvicorn", "awesome_project.webhook.main:app", "--host", "0.0.0.0", "--port", "10000"]