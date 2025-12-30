FROM python:3.13-alpine3.20

RUN apk --no-cache add gcc build-base git openssl-dev libffi-dev dcron

ENV APP_HOME=/app
WORKDIR ${APP_HOME}

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /uvx /bin/

ARG UV_EXTRA_ARGS="--no-dev"

# install deps
COPY pyproject.toml uv.lock ${APP_HOME}/
RUN uv sync --frozen --no-cache ${UV_EXTRA_ARGS} --compile-bytecode

# set the virtualenv
ENV VIRTUAL_ENV=${APP_HOME}/.venv
ENV PATH=${APP_HOME}:${APP_HOME}/.venv/bin:$PATH

COPY src/ ${APP_HOME}/

COPY src/cron/cron.txt /etc/crontabs/root
RUN chmod 600 /etc/crontabs/root  # permissions for cron
RUN touch /var/log/cron.log  # log file for cron
CMD ["crond", "-f"]

ENV PYTHONIOENCODING="UTF-8"
ENV PYTHONPATH "${APP_HOME}/src/:${PYTHONPATH}"

EXPOSE 8000

ARG version=unknown
RUN echo $version && sed -i "s/##VERSION##/$version/g" catalog/__init__.py

CMD ["gunicorn", "catalog.api:application", "--bind", "0.0.0.0:8000", "--worker-class", "aiohttp.GunicornWebWorker", "--graceful-timeout=60", "--timeout=360"]