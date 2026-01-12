FROM python:3.13-alpine3.20

RUN apk --no-cache add gcc build-base git openssl-dev libffi-dev dcron

ENV APP_HOME=/app
ENV UV_PROJECT_ENVIRONMENT=$APP_HOME/.venv
ENV PATH=$UV_PROJECT_ENVIRONMENT/bin:$PATH
ENV PYTHONIOENCODING="UTF-8"

WORKDIR $APP_HOME

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /uvx /bin/

# install dependenices
ARG UV_EXTRA_ARGS="--no-dev"
COPY pyproject.toml uv.lock $APP_HOME/
RUN uv sync --frozen --no-cache $UV_EXTRA_ARGS --compile-bytecode

# copy project files
ENV PYTHONPATH=$APP_HOME/src/:$PYTHONPATH
COPY src/ $APP_HOME/

COPY src/cron/cron.txt /etc/crontabs/root
RUN chmod 600 /etc/crontabs/root  # permissions for cron
RUN touch /var/log/cron.log  # log file for cron
CMD ["crond", "-f"]

# run project
ARG version=unknown
RUN echo $version && sed -i "s/##VERSION##/$version/g" catalog/__init__.py
EXPOSE 8000
CMD ["gunicorn", "catalog.api:application", "--bind", "0.0.0.0:8000", "--worker-class", "aiohttp.GunicornWebWorker", "--graceful-timeout=60", "--timeout=360"]