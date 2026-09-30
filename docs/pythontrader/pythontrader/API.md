# API
`GET /health` returns service status and current execution mode. `GET /v1/state` returns marked portfolio state and telemetry. `POST /v1/step` advances the deterministic feed by a bounded number of frames. `GET /v1/orders` exposes the in-memory order lifecycle ledger for inspection and tests.
