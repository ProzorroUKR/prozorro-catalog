FROM python:3.9-slim as base

RUN pip install --upgrade pip

WORKDIR /app
RUN apt-get update && apt-get install -y git
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY swagger /swagger
EXPOSE 80

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
