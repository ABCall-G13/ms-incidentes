FROM debian:12-slim AS build
RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends --yes python3-venv gcc libpython3-dev && \
    python3 -m venv /venv && \
    /venv/bin/pip install --upgrade pip setuptools wheel

FROM build AS build-venv

COPY requirements.txt /requirements.txt

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN /venv/bin/pip install --disable-pip-version-check -r /requirements.txt && \
    /venv/bin/pip install debugpy 

FROM gcr.io/distroless/python3-debian12 as production
COPY --from=build-venv /venv /venv

COPY . /app
WORKDIR /app

EXPOSE 8080

ENTRYPOINT ["/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]