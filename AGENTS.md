# Agent Instructions

`PROJECT_SPEC.md` is the authoritative specification for this project.

## Working rules

- Read `PROJECT_SPEC.md` before making architectural decisions.
- Read `IMPLEMENTATION_STATUS.md` before starting a phase.
- Implement only the requested phase.
- Keep ML and federated-learning code in Python.
- Keep application APIs in Node.js/Express.
- Keep the frontend in React.
- Use MongoDB for application persistence.
- Never send raw operator training records to the federated coordinator.
- Do not fabricate data, metrics, predictions, experiment results, or service status.
- Do not claim a feature works until it has been tested.
- Update `IMPLEMENTATION_STATUS.md` after each completed phase.
- Update `EXPERIMENT_LOG.md` only for experiments that were actually run.

Temporary mocks must be isolated, documented, and clearly marked as test-only.
