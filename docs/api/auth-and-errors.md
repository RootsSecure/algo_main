# Auth Rules and Error Model

## Auth behavior

- All protected endpoints require `Authorization: Bearer <token>`.
- Access tokens are required for normal API calls.
- Refresh tokens are accepted only by the refresh endpoint.

## Common HTTP statuses

- `200`: success
- `400`: invalid request or duplicate entity
- `401`: missing or invalid token
- `403`: role is not allowed
- `404`: requested entity not found

## Error payload style

FastAPI returns a `detail` field for handled HTTP exceptions. Example:

```json
{"detail": "Property not found"}
```

## Role expectations

- Owners can manage their own properties and participate in incident actions
- Delegates can access assigned properties but should not be treated as ops admins
- Ops admins can verify incidents and create dispatches
