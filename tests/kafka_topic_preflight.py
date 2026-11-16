"""Read-only Kafka topic preflight for explicitly approved live demos."""

from confluent_kafka.admin import AdminClient


def require_existing_topics(bootstrap_servers, topic_names):
    """Fail closed unless all required Kafka topics already exist."""
    names = tuple(topic_names)

    if not names or any(
        not isinstance(name, str) or not name.strip()
        for name in names
    ):
        raise ValueError("Nonempty Kafka topic names are required")

    admin = AdminClient({
        "bootstrap.servers": bootstrap_servers,
        "allow.auto.create.topics": False,
    })

    metadata = admin.list_topics(timeout=10)

    missing = [
        name
        for name in names
        if name not in metadata.topics
        or metadata.topics[name].error is not None
    ]

    if missing:
        raise RuntimeError(
            "STOP: Required isolated Kafka topics do not exist: "
            + ", ".join(missing)
        )

    return names
