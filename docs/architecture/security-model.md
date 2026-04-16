# Security Model

## Authentication

- JWT access and refresh tokens
- Password hashing using PBKDF2-HMAC-SHA256 with per-password salt
- Role-aware access dependencies for protected routes

## Roles

- `owner`: full control over owned properties
- `delegate`: delegated visibility after invite acceptance and assignment
- `installer`: reserved for later install-specific workflows
- `partner`: reserved for partner-specific authenticated surfaces later
- `ops_admin`: operational authority for verification and dispatch decisions

## Security controls in the current codebase

- Passwords are never stored in plaintext
- Protected endpoints require bearer tokens
- Important actions create audit log entries
- Evidence records track checksum and storage reference metadata

## Future hardening items

- Rotate secrets per environment
- Add token revocation or rotation storage for refresh tokens
- Enforce stronger invite expiration semantics
- Introduce per-tenant media access policies
- Add rate limiting and IP/device reputation checks at the API gateway layer
