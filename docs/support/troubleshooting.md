# Troubleshooting

## Migration fails
- Ensure the virtual environment is active
- Confirm `.env` points to a valid SQLite path
- Run `python -B -m alembic upgrade head`

## Login fails for default users
- Confirm the schema exists before app startup so seeding can run
- Verify `.env` credentials if changed

## Alerts do not create incidents
- Confirm the property exists and the alert payload has a valid `property_id`
- Check that the alert type is one of the supported normalized values

## Offline devices list is empty when expected
- Confirm the device has not posted a recent heartbeat
- Verify the query window used by the `minutes` parameter

## Tests behave differently from local database runs
- The test suite uses in-memory SQLite for isolation
- Local development uses a file-backed SQLite database under `data/`
