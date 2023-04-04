FROM python:3.9-alpine3.14 as base

RUN pip install --upgrade pip

WORKDIR /app
RUN apk --no-cache add gcc build-base git openssl-dev libffi-dev
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY swagger /app/swagger
COPY migrations /app/migrations
COPY cron /app/cron
RUN /usr/bin/crontab cron/cron.txt
EXPOSE 8000

FROM base as test_base

COPY tests/requirements.txt ./test-requirements.txt
RUN pip install -r test-requirements.txt

FROM base as prod

ADD src/ .
ARG version=unknown
RUN echo $version && sed -i "s/##VERSION##/$version/g" catalog/__init__.py

FROM test_base as test

ADD src/ .
ADD tests/ tests/
ARG version=unknown
RUN echo $version && sed -i "s/##VERSION##/$version/g" catalog/__init__.py

FROM prod
