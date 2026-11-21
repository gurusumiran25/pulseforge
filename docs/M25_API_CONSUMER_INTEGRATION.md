# M25 — API to consumer to warehouse boundary integration

This milestone tests a generated customer journey through the actual FastAPI batch route, Pydantic validation, producer publish interface, the real consumer `process_message` method, SQLite persistence, and the existing Silver/Gold SQL views.

The Kafka broker is replaced with a deterministic in-memory double and the consumer commit API with a recording double. Therefore the test **does not** verify real Redpanda network delivery, partitions, rebalances, delivery callbacks, or broker offset persistence. Those require the dedicated Redpanda integration suite and a future full-path CI test.

All SQLite files are disposable pytest fixtures. The test also verifies duplicate-message replay does not inflate warehouse counts. The normal API dependency override is restored in a `finally` block.

This test is an integration contract test across application boundaries, not a complete production-like distributed E2E test.
