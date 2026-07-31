"""Optional InfluxDB writer for mqtt-logger.

Listens for MQTT messages on topics matching a configurable regex (default:
``hal9k/<device>/sensor/<sensor_name>/state``), parses the payload as a float,
and writes the value as an InfluxDB point in real-time.

The writer is a no-op when InfluxDB is not configured.
"""

from __future__ import annotations

import logging
import math
import re

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS

    _INFLUXDB_AVAILABLE = True
except ImportError:
    _INFLUXDB_AVAILABLE = False

log = logging.getLogger(__name__)

DEFAULT_TOPIC_REGEX = r"^hal9k/([^/]+)/sensor/([^/]+)/state$"


class InfluxDBWriter:
    """Write matching MQTT sensor readings to InfluxDB.

    Parameters
    ----------
    url:
        InfluxDB server URL, e.g. ``https://influxdb.example.com/``.
    token:
        InfluxDB API token.
    bucket:
        Destination bucket name.
    org:
        Organisation name (may be empty for single-org OSS instances).
    topic_regex:
        Regular expression with two capture groups ``(device, sensor)``
        used to filter topics.  Defaults to the hal9k sensor state pattern.
    """

    def __init__(
        self,
        url: str,
        token: str,
        bucket: str,
        org: str = "",
        topic_regex: str = DEFAULT_TOPIC_REGEX,
    ) -> None:
        if not _INFLUXDB_AVAILABLE:
            raise ImportError(
                "influxdb-client is required for InfluxDB support. "
                "Install it with: uv add 'mqtt-logger[influxdb]'"
            )

        self._bucket = bucket
        self._re = re.compile(topic_regex)

        self._client = InfluxDBClient(url=url, token=token, org=org)
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)

        log.info("InfluxDB writer connected to %s (bucket=%s)", url, bucket)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(self, topic: str, payload: bytes) -> None:
        """Write a sensor reading to InfluxDB if the topic and payload match."""
        m = self._re.match(topic)
        if not m:
            return

        try:
            payload_str = payload.decode("utf-8")
            value = float(payload_str)
        except (UnicodeDecodeError, ValueError, TypeError):
            return

        if math.isnan(value) or math.isinf(value):
            return

        device = m.group(1)
        sensor = m.group(2)

        point = (
            Point(topic)
            .tag("device", device)
            .tag("sensor", sensor)
            .field("value", value)
        )

        try:
            self._write_api.write(bucket=self._bucket, record=point)
            log.debug("InfluxDB point written: %s value=%s", topic, value)
        except Exception:
            log.exception("Failed to write InfluxDB point for topic %s", topic)

    def close(self) -> None:
        """Flush and close the InfluxDB client."""
        try:
            self._client.close()
            log.info("InfluxDB writer closed")
        except Exception:
            log.exception("Error closing InfluxDB client")
