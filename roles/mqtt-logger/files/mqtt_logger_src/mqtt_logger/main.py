"""MQTT logger entry point."""

from __future__ import annotations

import logging
import signal
import sys

import paho.mqtt.client as mqtt
from rich.logging import RichHandler

from mqtt_logger.config import parse_args
from mqtt_logger.influxdb_writer import DEFAULT_TOPIC_REGEX, InfluxDBWriter
from mqtt_logger.writer import JsonlWriter

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    config = parse_args(argv)

    log.info(
        "Starting mqtt-logger | broker=%s:%d topic=%s log_dir=%s max_file=%d B max_total=%d B",
        config.broker_host,
        config.broker_port,
        config.topic,
        config.log_dir,
        config.max_file_bytes,
        config.max_total_bytes,
    )

    writer = JsonlWriter(
        log_dir=config.log_dir,
        max_file_bytes=config.max_file_bytes,
        max_total_bytes=config.max_total_bytes,
    )

    influxdb_writer: InfluxDBWriter | None = None
    if config.influxdb_enabled:
        influxdb_writer = InfluxDBWriter(
            url=config.influxdb_url,  # type: ignore[arg-type]
            token=config.influxdb_token,  # type: ignore[arg-type]
            bucket=config.influxdb_bucket,  # type: ignore[arg-type]
            org=config.influxdb_org,
            topic_regex=config.influxdb_topic_regex or DEFAULT_TOPIC_REGEX,
        )
    else:
        log.info("InfluxDB output disabled (INFLUXDB_URL / INFLUXDB_TOKEN / INFLUXDB_BUCKET not set)")

    # --- paho-mqtt v2 callbacks ---

    def on_connect(client: mqtt.Client, userdata: object, flags: object, reason_code: mqtt.ReasonCode, properties: object) -> None:
        if reason_code.is_failure:
            log.error("Connection failed: %s", reason_code)
            sys.exit(1)
        log.info("Connected to %s:%d — subscribing to '%s'", config.broker_host, config.broker_port, config.topic)
        client.subscribe(config.topic)

    def on_message(client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        log.debug("msg: %s", msg.topic)
        writer.write(msg.topic, msg.payload)
        if influxdb_writer is not None:
            influxdb_writer.write(msg.topic, msg.payload)

    def on_disconnect(client: mqtt.Client, userdata: object, flags: object, reason_code: mqtt.ReasonCode, properties: object) -> None:
        if reason_code.is_failure:
            log.warning("Unexpected disconnect: %s", reason_code)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    if config.username:
        client.username_pw_set(config.username, config.password)

    # Graceful shutdown on SIGINT / SIGTERM
    def _shutdown(signum: int, frame: object) -> None:
        log.info("Shutting down…")
        client.disconnect()
        client.loop_stop()
        writer.close()
        if influxdb_writer is not None:
            influxdb_writer.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    client.connect(config.broker_host, config.broker_port, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
