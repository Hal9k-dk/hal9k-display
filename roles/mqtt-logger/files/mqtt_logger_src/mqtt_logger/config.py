"""Configuration for mqtt-logger.

Values are read from CLI arguments, with environment variable fallbacks.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

# Defaults
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 1883
DEFAULT_LOG_DIR = "logs"
DEFAULT_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MiB
DEFAULT_MAX_TOTAL_BYTES = 1 * 1024 * 1024 * 1024  # 1 GiB
DEFAULT_TOPIC = "#"


@dataclass
class Config:
    broker_host: str
    broker_port: int
    username: str | None
    password: str | None
    topic: str
    log_dir: str
    max_file_bytes: int
    max_total_bytes: int
    # InfluxDB (all optional — feature is disabled when influxdb_url is unset)
    influxdb_url: str | None
    influxdb_token: str | None
    influxdb_bucket: str | None
    influxdb_org: str
    influxdb_topic_regex: str | None

    @property
    def influxdb_enabled(self) -> bool:
        """Return True when all required InfluxDB settings are present."""
        return bool(self.influxdb_url and self.influxdb_token and self.influxdb_bucket)


def parse_args(argv: list[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(
        description="Subscribe to MQTT topics and log messages to JSONL files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--host",
        default=os.environ.get("MQTT_HOST", DEFAULT_HOST),
        help="MQTT broker hostname or IP (env: MQTT_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MQTT_PORT", DEFAULT_PORT)),
        help="MQTT broker port (env: MQTT_PORT)",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("MQTT_USERNAME"),
        help="MQTT username (env: MQTT_USERNAME)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("MQTT_PASSWORD"),
        help="MQTT password (env: MQTT_PASSWORD)",
    )
    parser.add_argument(
        "--topic",
        default=os.environ.get("MQTT_TOPIC", DEFAULT_TOPIC),
        help="MQTT topic filter to subscribe to (env: MQTT_TOPIC)",
    )
    parser.add_argument(
        "--log-dir",
        default=os.environ.get("MQTT_LOG_DIR", DEFAULT_LOG_DIR),
        help="Directory to write JSONL log files (env: MQTT_LOG_DIR)",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=int(os.environ.get("MQTT_MAX_FILE_BYTES", DEFAULT_MAX_FILE_BYTES)),
        metavar="BYTES",
        help="Rotate log file when it exceeds this size in bytes (env: MQTT_MAX_FILE_BYTES)",
    )
    parser.add_argument(
        "--max-total-size",
        type=int,
        default=int(os.environ.get("MQTT_MAX_TOTAL_BYTES", DEFAULT_MAX_TOTAL_BYTES)),
        metavar="BYTES",
        help="Delete oldest log files to keep total directory usage at or below this size in bytes (env: MQTT_MAX_TOTAL_BYTES)",
    )

    # InfluxDB options
    influxdb_group = parser.add_argument_group("InfluxDB (optional)")
    influxdb_group.add_argument(
        "--influxdb-url",
        default=os.environ.get("INFLUXDB_URL"),
        help="InfluxDB server URL (env: INFLUXDB_URL). Enables InfluxDB output when set together with --influxdb-token and --influxdb-bucket.",
    )
    influxdb_group.add_argument(
        "--influxdb-token",
        default=os.environ.get("INFLUXDB_TOKEN"),
        help="InfluxDB API token (env: INFLUXDB_TOKEN)",
    )
    influxdb_group.add_argument(
        "--influxdb-bucket",
        default=os.environ.get("INFLUXDB_BUCKET"),
        help="InfluxDB destination bucket (env: INFLUXDB_BUCKET)",
    )
    influxdb_group.add_argument(
        "--influxdb-org",
        default=os.environ.get("INFLUXDB_ORG", ""),
        help="InfluxDB organisation (env: INFLUXDB_ORG)",
    )
    influxdb_group.add_argument(
        "--influxdb-topic-regex",
        default=os.environ.get("INFLUXDB_TOPIC_REGEX"),
        help="Regex (two capture groups: device, sensor) selecting topics written to InfluxDB"
             " (env: INFLUXDB_TOPIC_REGEX). Defaults to the hal9k sensor state pattern.",
    )

    args = parser.parse_args(argv)

    return Config(
        broker_host=args.host,
        broker_port=args.port,
        username=args.username,
        password=args.password,
        topic=args.topic,
        log_dir=args.log_dir,
        max_file_bytes=args.max_file_size,
        max_total_bytes=args.max_total_size,
        influxdb_url=args.influxdb_url,
        influxdb_token=args.influxdb_token,
        influxdb_bucket=args.influxdb_bucket,
        influxdb_org=args.influxdb_org,
        influxdb_topic_regex=args.influxdb_topic_regex,
    )
