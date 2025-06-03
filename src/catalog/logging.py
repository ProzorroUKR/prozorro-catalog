import logging
import sys
from contextvars import ContextVar

from aiohttp.abc import AbstractAccessLogger
from pythonjsonlogger import jsonlogger

request_id_var = ContextVar('request_id')


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, {})
        if not log_record.get("message") and message_dict:
            log_record['message'] = message_dict

        log_record['levelname'] = record.levelname
        log_record['name'] = record.name
        log_record['funcName'] = record.funcName


def setup_logging():

    # get base log record factory to extend it
    base_factory = logging.getLogRecordFactory()

    # custom factory will add extra fields to log records
    # so we can later use them in format
    def custom_factory(*args, **kwargs):
        record = base_factory(*args, **kwargs)
        record.request_id = request_id_var.get("")
        return record

    # setting extended factory instead the default
    logging.setLogRecordFactory(custom_factory)

    formatter = CustomJsonFormatter(json_ensure_ascii=False, timestamp=True)

    # Handler for stdout (DEBUG/INFO/WARNING)
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    stdout_handler.setFormatter(formatter)

    # Handler for stderr (ERROR/CRITICAL)
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.DEBUG, handlers=[stdout_handler, stderr_handler])

    logging.getLogger('pymongo').setLevel(logging.WARNING)

    # serve alternative logging for uncaught exceptions
    def exception_logging(exc_type, exc_value, exc_traceback):
        logging.exception(f'Exception {exc_type} raised', exc_info=exc_value)

    # override writing uncaught exceptions to stderr by using JSON logging
    sys.excepthook = exception_logging


# custom aiohttp access logger with request-id added
LOG_EXCLUDED = {
    "/api/ping",  # api ping
    "/api/metrics",  # metrics
}


class AccessLogger(AbstractAccessLogger):

    def log(self, request, response, time):
        remote = request.headers.get('X-Forwarded-For', request.remote)
        refer = request.headers.get('Referer', '-')
        user_agent = request.headers.get('User-Agent', '-')
        if request.path not in LOG_EXCLUDED:
            self.logger.info(f'{remote} '
                             f'"{request.method} {request.path} {response.status}'
                             f'{response.body_length} {refer} {user_agent} '
                             f'{time:.6f}s"')
