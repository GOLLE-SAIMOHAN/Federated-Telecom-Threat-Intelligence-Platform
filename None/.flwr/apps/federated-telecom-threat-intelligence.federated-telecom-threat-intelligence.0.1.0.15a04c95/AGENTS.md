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

# CRITICAL: AI CREDIT OPTIMIZATION RULES

These rules are mandatory for every development task in this repository.

The developer has a very limited AI credit budget. Your primary responsibility is to complete tasks correctly while minimizing AI usage, unnecessary tool calls, context consumption, and code generation.

## 1. Minimize AI usage

- Use the smallest possible amount of reasoning and output needed to complete the task.
- Never perform unnecessary repository-wide inspections when relevant files are already known.
- Avoid repeatedly reading files that have not changed.
- Do not regenerate existing code.
- Do not explain obvious code unnecessarily.
- Avoid lengthy progress reports.
- Do not generate multiple alternative implementations unless explicitly requested.
- Prefer simple, reliable solutions over unnecessarily complex architectures.

## 2. Inspect before implementing

- Inspect only the files directly relevant to the requested task.
- Reuse existing modules, utilities, components, APIs, and configurations.
- Check existing dependencies before suggesting new installations.
- Never rebuild an already implemented feature.
- Identify the exact issue before modifying code.

## 3. Strict task boundaries

- Complete only the task explicitly assigned.
- Do not independently start additional phases.
- Do not refactor unrelated files.
- Do not modify working functionality unnecessarily.
- Do not make speculative improvements.
- If a blocker exists, report it instead of generating unnecessary code.

## 4. Efficient code generation

- Make focused changes rather than rewriting entire files.
- Avoid duplicate functions and components.
- Follow existing coding conventions.
- Prefer reusable components and shared utilities.
- Avoid unnecessary abstractions.
- Do not add dependencies when existing packages can solve the problem.
- Avoid generating boilerplate that is not required.

## 5. Efficient testing

- Run the smallest relevant test suite first.
- Do not repeatedly execute the entire test suite after every minor change.
- Run full tests at appropriate integration milestones.
- Never claim that tests passed unless they were actually executed.
- Report only relevant test results and errors.

## 6. Efficient debugging

- Read the exact error and investigate its root cause.
- Do not randomly modify multiple files.
- Do not repeatedly try different solutions without evidence.
- Fix the root cause with the smallest safe change.
- Avoid reinstalling all dependencies unless necessary.

## 7. Context management

At the end of each completed task, provide a short handover containing:

1. What was changed.
2. Files modified.
3. Tests executed and results.
4. Remaining blockers.
5. The next recommended task.

Update `IMPLEMENTATION_STATUS.md` only when actual implementation status changes.

Maintain the existing project documentation as the source of truth.

When starting a new conversation, read the relevant project instructions and current implementation status instead of repeating the entire development history.

## 8. Approval requirements

- Ask before making destructive changes.
- Ask before introducing major dependencies.
- Ask before changing architecture.
- Do not implement additional features without approval.

## 9. Output discipline

Keep responses concise and technical.

Do not produce lengthy explanations, repeated summaries, or unnecessary documentation.

Prioritize implementation correctness, existing functionality, and minimum AI credit consumption.

**FINAL RULE: Every task must be completed using the minimum reasonable AI effort and the smallest safe code change.**