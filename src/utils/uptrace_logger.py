import logging

import grpc
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from src.consts import APP_SOURCE


def add_uptrace_logging(dsn):
    resource = Resource(
        attributes={
            "service.name": "sysblokbot",
            "service.version": "1.0.0",
            "deployment.environment": APP_SOURCE,
        }
    )
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    exporter = OTLPLogExporter(
        endpoint="otlp.uptrace.dev:4317",
        headers=(("uptrace-dsn", dsn),),
        timeout=5,
        compression=grpc.Compression.Gzip,
    )
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)

    logging.getLogger().addHandler(handler)
