# Hospital System (DeviceCare)

## Run with Docker Compose

```bash
docker compose up --build
```

Then open: http://localhost:8000

## Notes
- The container runs database migrations automatically at startup.
- Source code is mounted into the container for development (`.:/app`).
