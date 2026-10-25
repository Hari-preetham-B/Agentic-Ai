# Test Plan — CareerTwin

## Future testing strategy

- Frontend unit tests
- Backend unit tests
- API tests
- Pydantic validation tests
- Agent workflow tests
- Evidence retrieval tests
- Claim classification tests
- Confidence-engine tests
- Integration tests
- End-to-end tests
- Security / authorization tests

## This stage (foundation)

Only the minimum tests needed to validate the foundation are implemented:

- backend starts
- `/health` works
- frontend builds
- frontend routes render

### Implemented tests
- `apps/api/tests/test_health.py` — `GET /health` returns `status: ok` and the
  service name; root endpoint returns service meta.

### Validation commands

Backend:
```bash
cd apps/api
pip install -e .
pip install pytest
pytest
```

Frontend:
```bash
cd apps/web
npm install
npm run lint
npm run build
```

Backend server check:
```bash
cd apps/api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
curl http://localhost:8000/health
```

## Status
Foundation-stage tests implemented. Future phases add the full strategy above.
