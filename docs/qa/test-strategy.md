# Test Strategy

## Testing layers

### Unit
- severity classification
- token generation and decoding
- password hashing verification

### API
- owner login and token use
- property creation and zone creation
- device registration and heartbeat
- alert ingestion and incident creation
- partner dispatch and incident export

### Integration
- delegate invite, accept, and assignment
- health summary retrieval

## Philosophy

The MVP prioritizes confidence in the alert-to-incident path because that is the product's highest-risk workflow. Tests should prove that alerts become incidents, incidents can be verified, and dispatch actions result in consistent state.
