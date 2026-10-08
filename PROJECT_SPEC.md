# PROJECT_SPEC.md

# Federated Telecom Threat Intelligence Platform

## 1. Project Identity

**Project Name:** Federated Telecom Threat Intelligence Platform

**Project Type:** B.Tech Final-Year Major Project / Research Prototype

**Primary Domain:** Telecom Cybersecurity, Federated Learning, Cyber Threat Intelligence, Distributed Machine Learning

**Primary Goal:**
Build a research-grade prototype that allows multiple simulated telecom operators to collaboratively detect and learn from cyber threats without centralizing their raw network-security data.

This project is a simulated telecom cybersecurity platform. It is NOT intended to directly integrate with real telecom infrastructure, mobile network cores, SIM systems, radio equipment, or production operator networks.

---

# 2. Problem Statement

Telecom operators generate sensitive network and security data that can contain proprietary information and potentially sensitive customer-related information.

A conventional centralized cybersecurity system would require operators to send their raw security/network data to a central location. This creates privacy, security, regulatory, ownership, and competitive concerns.

The proposed platform demonstrates an alternative architecture:

- Each telecom operator keeps its raw security data locally.
- Each operator performs local preprocessing and machine-learning training.
- Operators participate in federated learning.
- A central federated coordinator aggregates model updates rather than collecting raw training records.
- A shared/global model can therefore benefit from patterns learned across multiple operators.
- Detected threats can additionally be represented as structured Cyber Threat Intelligence (CTI).
- Appropriate threat intelligence can be propagated between participating operators.
- A web dashboard provides visibility into operators, threats, FL rounds, model metrics, and CTI activity.

The system demonstrates privacy-preserving collaborative threat detection rather than claiming absolute privacy.

---

# 3. Core Concept

The fundamental system is:

    Operator A ─┐
    Operator B ─┤
    Operator C ─┼──> Federated Learning Coordinator
    Operator D ─┘             │
                              │
                           FedAvg
                              │
                              ▼
                        Global Model
                              │
                              ▼
                    Threat Intelligence
                              │
                              ▼
                         Backend/API
                              │
                              ▼
                           MongoDB
                              │
                              ▼
                       React Dashboard

Each operator represents an independent telecom organization.

The operators must behave as separate data owners.

The project must demonstrate that raw operator datasets do not need to be transferred to the federated coordinator for collaborative model training.

---

# 4. Main Objectives

## Objective 1 — Privacy-Preserving Collaboration

Allow multiple simulated telecom operators to collaboratively train a machine-learning model while keeping their raw training data within their respective operator environments.

## Objective 2 — Telecom Threat Detection

Use a telecom/5G-oriented intrusion-detection dataset to detect network attacks and security threats.

## Objective 3 — Federated Learning

Implement actual federated learning using a real FL framework and FedAvg-style aggregation.

The system must NOT merely simulate FL with hardcoded values.

## Objective 4 — Cyber Threat Intelligence

Convert locally detected threats into structured threat-intelligence records that can be shared appropriately between participating operators.

## Objective 5 — Distributed Operator Simulation

Simulate at least four independent telecom operators:

- Operator A
- Operator B
- Operator C
- Operator D

## Objective 6 — Web Dashboard

Provide a React-based dashboard showing the state of the distributed cybersecurity system.

## Objective 7 — Experimental Evaluation

Compare centralized, local, and federated approaches using actual measured results.

The project should support meaningful experiments such as:

- centralized vs federated learning
- IID vs non-IID data
- different numbers of federated rounds
- operator participation
- model convergence
- communication overhead
- training time
- detection performance

## Objective 8 — Containerized Deployment

Use Docker and Docker Compose to reproduce the distributed environment locally.

---

# 5. Dataset

## Primary Dataset

**5G-NIDD — 5G Wireless Network Intrusion Detection Dataset**

The dataset is selected because the project is focused on telecom/5G cybersecurity.

Potential attack categories include network attacks such as:

- ICMP Flood
- UDP Flood
- SYN Flood
- HTTP Flood
- Slowrate DoS
- SYN Scan
- TCP Connect Scan
- UDP Scan

The implementation must inspect the actual downloaded dataset before assuming exact column names, labels, class distributions, or file structure.

DO NOT hardcode assumptions about the dataset without verifying the actual files.

---

# 6. Dataset Processing

The dataset pipeline must support:

1. Dataset loading
2. Dataset validation
3. Column inspection
4. Missing-value analysis
5. Duplicate analysis where appropriate
6. Feature selection
7. Categorical encoding where required
8. Numerical preprocessing where required
9. Label preparation
10. Train/test splitting
11. Reproducible random seeds
12. Dataset partitioning among operators

The pipeline must be reusable.

Do not create different preprocessing logic manually for each operator.

All operators should use the same preprocessing specification unless an experiment explicitly requires otherwise.

---

# 7. Operator Data Isolation

The four operators represent independent data owners.

Each operator must have access only to its own local training data during federated training.

Example:

    Operator A
        └── local dataset A
             └── local model

    Operator B
        └── local dataset B
             └── local model

    Operator C
        └── local dataset C
             └── local model

    Operator D
        └── local dataset D
             └── local model

The federated coordinator must not receive raw dataset records.

The architecture must make this boundary explicit.

---

# 8. Data Partitioning

The project must support two major experimental configurations.

## 8.1 IID Configuration

The dataset is distributed approximately uniformly among operators.

This provides a baseline federated-learning scenario.

## 8.2 Non-IID Configuration

Operators receive heterogeneous data distributions.

For example:

- Operator A may contain more DoS traffic.
- Operator B may contain more scanning traffic.
- Operator C may contain a different mixture.
- Operator D may contain another distribution.

The exact distribution must be generated from actual dataset labels and recorded.

Do not fabricate distributions or experimental results.

---

# 9. Machine Learning

## Primary Model

Use:

**Random Forest**

The model is selected as the initial project baseline because it is appropriate for tabular intrusion-detection data and is practical for a B.Tech prototype.

The architecture should remain modular so another model can be evaluated later if necessary.

---

# 10. Centralized Baseline

Before federated learning is implemented, create a centralized baseline.

The centralized model should train using the appropriate combined training data.

Record actual:

- Accuracy
- Precision
- Recall
- F1-score
- Confusion matrix
- False-positive rate where applicable
- False-negative rate where applicable
- Training time

The centralized baseline exists only for comparison.

It does not represent the privacy-preserving architecture.

---

# 11. Local Models

Each operator must also be capable of independently training a local model.

Example:

    Operator A → Local Model A
    Operator B → Local Model B
    Operator C → Local Model C
    Operator D → Local Model D

Each local model must be evaluated using actual test/evaluation data according to the experiment configuration.

Record actual performance metrics.

---

# 12. Federated Learning Architecture

Use **Flower** as the federated-learning framework.

Use **FedAvg** as the initial aggregation strategy.

The federated workflow must be real.

## Federated Round

The intended flow is:

1. Federated server initializes Global Model v1.
2. Global Model v1 is distributed to participating operators.
3. Each operator loads its local data.
4. Each operator trains locally.
5. Each operator evaluates locally.
6. Each operator sends the required model parameters/updates and metrics.
7. Federated server aggregates updates using FedAvg.
8. Server produces Global Model v2.
9. New global model is distributed.
10. Process repeats for multiple rounds.

At minimum, the prototype should support multiple FL rounds, with 5 or more rounds used for the initial experiment.

The implementation must log:

- round number
- participating operators
- local training status
- local sample counts
- aggregation status
- global model version
- global metrics where applicable
- training time
- communication-related measurements where practical

---

# 13. Federated Learning Privacy Boundary

The following rule is mandatory:

**Raw operator training records must never be sent to the federated coordinator.**

The FL coordinator may receive information necessary for federated learning, such as:

- model parameters
- model updates
- parameter metadata
- sample counts required for weighted aggregation
- evaluation metrics
- training status

Do not send:

- raw network records
- raw dataset rows
- raw customer information
- unnecessary operator logs

The code should make the data boundary easy to audit.

---

# 14. Privacy Claims

Do NOT claim:

- absolute privacy
- mathematically guaranteed privacy
- complete protection against model-update attacks
- regulatory compliance unless specifically implemented and verified
- production telecom security

Federated learning reduces the need to centralize raw data, but model updates can potentially leak information under certain threat models.

If stronger privacy mechanisms are added later, such as:

- secure aggregation
- differential privacy
- encryption
- MPC

they must be implemented and experimentally evaluated before claiming them.

Do not claim these technologies merely because they appear in project documentation.

---

# 15. Federated Model Evaluation

The project must support comparison of:

### A. Centralized Model
One model trained with centralized training data.

### B. Independent Local Models
Four models trained independently.

### C. Federated Global Model
A model produced through actual federated training.

Metrics should include:

- Accuracy
- Precision
- Recall
- F1-score
- Confusion matrix
- False-positive rate
- False-negative rate
- Training time
- Number of rounds
- Convergence behavior
- Communication overhead where measurable

All reported numbers must come from actual experiment execution.

---

# 16. Threat Detection

When an operator's local model identifies a threat, the system should be able to create a structured threat event.

Example:

    Operator A
        ↓
    Local prediction
        ↓
    Attack detected
        ↓
    Threat record created
        ↓
    CTI generation
        ↓
    Appropriate propagation
        ↓
    Other operators

Threat detection should be based on actual model outputs or actual simulated detection events.

Do not create fake threat detections merely to populate the dashboard.

For development/testing, controlled test fixtures may be used, but they must be explicitly identified as test data.

---

# 17. Cyber Threat Intelligence Layer

The CTI layer represents detected threats in structured form.

A threat record should support fields such as:

- threat_id
- category
- severity
- confidence
- timestamp
- source_operator
- indicators
- signature or threat pattern
- status
- propagation status
- affected operators where applicable

The exact schema can evolve during implementation.

The CTI system must not contain raw network logs unless explicitly required for a controlled local-only operation.

---

# 18. CTI Propagation

Example:

    Operator A detects:
        UDP Flood
        confidence = actual model confidence/derived score
        severity = calculated/defined severity

    CTI event:
        Threat ID
        Category
        Severity
        Confidence
        Indicator/signature
        Source Operator

The system can propagate the appropriate CTI information to other participating operators.

Other operators should be able to:

- receive the intelligence
- view it
- mark it as processed
- use it as part of simulated defensive intelligence

The system may simulate actions such as updating a threat-prevention rule.

Do not claim that the system directly modifies real telecom firewalls.

---

# 19. Backend

## Technology

Node.js + Express.js

The backend acts as the application/API layer.

The backend should not replace the Python ML/FL layer.

The backend should communicate with the ML/FL services through a clearly defined interface.

---

# 20. Backend Responsibilities

The backend should support APIs for:

### Operators
- operator list
- operator status
- operator health
- operator activity

### Threats
- active threats
- threat history
- threat details
- severity
- category
- confidence

### CTI
- CTI records
- CTI propagation
- CTI status
- threat intelligence history

### Federated Learning
- current FL round
- global model version
- round history
- participating operators
- training status
- aggregation status

### Metrics
- global model metrics
- operator metrics
- centralized baseline metrics
- experiment results

### System
- health check
- service status
- system summary

---

# 21. Database

## Technology

MongoDB

MongoDB should store application/platform information such as:

- operator metadata
- threat records
- CTI records
- FL round metadata
- model metrics
- experiment metadata
- activity/audit information
- system events where appropriate

MongoDB should NOT become a centralized dump of raw operator training datasets.

Raw operator datasets must remain in their respective local operator environments.

---

# 22. Frontend

## Technology

React.js

The frontend is a web-based cybersecurity dashboard.

The UI should be professional enough for a B.Tech major-project demonstration.

---

# 23. Main Dashboard

The dashboard should provide a high-level view of:

- number of operators
- operator health/status
- current FL round
- global model version
- model performance
- active threats
- threat severity
- threat categories
- recent CTI activity
- recent system events

All important values should come from backend APIs.

Do not hardcode live metrics.

---

# 24. Required Frontend Pages

The initial application should support:

## Login / Authentication

Basic authentication suitable for the academic prototype.

## Global Dashboard

Overall system status and key metrics.

## Operators

Show:

- Operator A
- Operator B
- Operator C
- Operator D

with status and relevant activity.

## Threat Intelligence

Show CTI records and propagation status.

## Threat Details

Show detailed information for a selected threat.

## Federated Learning

Show:

- current round
- model version
- participating operators
- round history
- training status
- aggregation status

## Model Metrics

Show:

- accuracy
- precision
- recall
- F1
- confusion matrix
- experiment comparisons

## Activity / Audit Log

Show relevant platform events.

---

# 25. Frontend Design Principles

The interface should be:

- clean
- professional
- responsive
- cybersecurity-oriented
- easy to demonstrate
- understandable to faculty/evaluators

Avoid unnecessary visual complexity.

Do not spend excessive development time on animations.

Functionality and correctness have higher priority than visual effects.

---

# 26. Authentication and Authorization

The project may implement basic role-aware authentication.

At minimum, application access should be structured so that future operator-specific permissions can be supported.

Possible roles:

- Administrator
- Operator

Do not implement complex enterprise IAM unless required.

---

# 27. Docker Architecture

The final system should be containerized.

Expected services:

    frontend
    backend
    mongodb
    federated-server
    operator-a
    operator-b
    operator-c
    operator-d

Docker Compose should provide the local distributed environment.

The system should ideally be startable with:

    docker compose up --build

The exact command may change if the implementation requires it.

---

# 28. Operator Containers

Each operator service should represent an independent operator environment.

An operator container should have:

- local dataset access
- local preprocessing
- local ML model
- local training capability
- connection to FL coordinator
- threat detection capability
- CTI interaction

The architecture should prevent accidental sharing of raw datasets.

---

# 29. Federated Server Container

The federated-server should:

- initialize the global model
- coordinate FL rounds
- select/accept participating clients
- receive model updates
- perform FedAvg
- produce updated global model
- record FL metadata
- expose appropriate status information to the rest of the platform

The federated server must not require raw operator datasets.

---

# 30. Service Communication

The architecture should clearly separate:

### ML/FL communication

Python services ↔ Flower

### Application communication

React ↔ Node/Express

### Persistence

Node/Express ↔ MongoDB

### ML/FL status integration

Python ML/FL services ↔ backend through a clearly defined mechanism.

Do not tightly couple all components unnecessarily.

---

# 31. Repository Structure

The final structure can evolve, but a reasonable organization is:

    federated-telecom-threat-intelligence/
    │
    ├── PROJECT_SPEC.md
    ├── AGENTS.md
    ├── IMPLEMENTATION_STATUS.md
    ├── EXPERIMENT_LOG.md
    ├── README.md
    │
    ├── ml/
    │   ├── data/
    │   ├── preprocessing/
    │   ├── models/
    │   ├── evaluation/
    │   ├── centralized/
    │   ├── federated/
    │   └── experiments/
    │
    ├── operators/
    │   ├── operator_a/
    │   ├── operator_b/
    │   ├── operator_c/
    │   └── operator_d/
    │
    ├── federated-server/
    │
    ├── backend/
    │
    ├── frontend/
    │
    ├── database/
    │
    ├── docker/
    │
    └── docker-compose.yml

The coding agent may improve the structure if there is a clear technical reason.

---

# 32. Experiment Logging

Create and maintain:

    EXPERIMENT_LOG.md

Every significant experiment should record:

- experiment name
- objective
- dataset
- dataset size
- feature count
- class distribution
- train/test split
- operator distribution
- model
- hyperparameters
- random seed
- FL configuration
- number of rounds
- actual metrics
- training time
- communication measurements where available
- observations
- limitations

Never manually invent experiment results.

---

# 33. Implementation Status

Maintain:

    IMPLEMENTATION_STATUS.md

Use it to track:

- completed components
- current phase
- tests passed
- known issues
- pending work
- experiment status

A feature is not "complete" merely because its code exists.

It should be considered complete only after appropriate testing.

---

# 34. Testing Strategy

The project must include tests for:

## Data
- dataset loading
- preprocessing
- label handling
- operator partitioning

## ML
- model training
- prediction
- evaluation
- model save/load

## Federated Learning
- server startup
- client connection
- local training
- parameter exchange
- FedAvg
- multiple rounds
- global model update

## CTI
- threat creation
- CTI generation
- CTI retrieval
- propagation
- status updates

## Backend
- API endpoints
- validation
- error handling
- database operations

## Frontend
- page loading
- API integration
- important UI flows

## Docker
- service startup
- service connectivity
- health checks
- persistence

## End-to-End

Verify:

    Dataset
      ↓
    Operators
      ↓
    Local ML
      ↓
    Federated Learning
      ↓
    Global Model
      ↓
    Threat Detection
      ↓
    CTI
      ↓
    Backend
      ↓
    MongoDB
      ↓
    React Dashboard

---

# 35. Security Principles

The prototype should follow reasonable secure-development practices.

Implement where appropriate:

- environment variables for secrets
- input validation
- API error handling
- authentication
- authorization
- secure configuration
- structured logging
- no credentials committed to Git
- no raw sensitive data in logs
- Docker isolation
- least-privilege principles where practical

Do not over-engineer enterprise security.

---

# 36. What This Project Is NOT

Do NOT turn this project into:

- a real telecom network controller
- a 4G/5G core implementation
- a real SIM security system
- a real radio/base-station implementation
- a production telecom firewall
- a national threat-intelligence exchange
- a complete commercial SIEM
- a full SOC platform
- a blockchain project
- a cryptocurrency project
- an unnecessary microservices architecture

The project should remain focused.

---

# 37. Research/Academic Positioning

The project should be presented as:

**A privacy-preserving federated cybersecurity research prototype for collaborative telecom threat detection and threat intelligence.**

The project demonstrates:

1. distributed data ownership
2. local machine learning
3. federated model aggregation
4. heterogeneous/non-IID data
5. cyber threat intelligence
6. distributed operator simulation
7. measurable cybersecurity performance
8. containerized deployment
9. web-based visualization

---

# 38. Important Architectural Distinction

The system is NOT simply:

    Telecom Operators
          ↓
    Central Database
          ↓
    Masked Functions

Instead, the main learning architecture is:

    Local Operator Data
          ↓
    Local Training
          ↓
    Model Updates
          ↓
    Federated Aggregation
          ↓
    Global Model

Threat intelligence is a separate but connected layer:

    Local Detection
          ↓
    Structured CTI
          ↓
    Privacy-conscious propagation
          ↓
    Other Operators

A central coordinator exists for federated learning, but it must not become a centralized raw-data repository.

---

# 39. Model Versioning

The system should conceptually track:

    Global Model v1
         ↓
    FL Round 1
         ↓
    Global Model v2
         ↓
    FL Round 2
         ↓
    Global Model v3
         ↓
    ...

The exact versioning implementation can vary.

The dashboard should make model progression understandable.

---

# 40. Reproducibility

Experiments should be reproducible as far as practical.

Use:

- fixed random seeds
- recorded configurations
- versioned experiment parameters
- documented dataset preparation
- documented model hyperparameters
- consistent evaluation methodology

Do not overwrite previous experimental results without recording the new configuration.

---

# 41. Performance Considerations

The project is intended to run on a student/developer machine.

Therefore:

- use manageable dataset subsets when necessary
- avoid unnecessarily large models
- avoid GPU dependency unless genuinely required
- avoid excessive Docker resource usage
- allow configurable dataset size
- allow configurable FL rounds
- keep development/testing fast

If a smaller subset is used for development, clearly distinguish it from the final experiment dataset.

---

# 42. Error Handling

All services should fail clearly.

Errors should include enough information for debugging without exposing sensitive information.

Do not silently ignore failures.

Do not return fake successful responses when an underlying service failed.

For example:

If an operator fails to connect to the FL server:

    status = failed/disconnected

not:

    status = training_success

---

# 43. No Fake Demonstration Logic

This is a critical rule.

The project dashboard must not display:

- fake FL rounds
- fake model accuracy
- fake threat counts
- fake operator status
- fake training progress
- fake CTI events

unless the data is explicitly identified as a test/demo fixture.

The final demonstration should use actual system outputs wherever possible.

---

# 44. Temporary Development Mocks

Mocks are allowed only when required to develop an unavailable component.

Every mock must be:

- clearly marked
- isolated
- documented
- replaceable

Before final integration, replace temporary mocks with real implementations where possible.

---

# 45. Dependency Policy

Use only technologies that contribute directly to the project.

Primary stack:

    Python
    Pandas
    NumPy
    Scikit-learn
    Flower
    Node.js
    Express.js
    MongoDB
    React
    Docker
    Docker Compose

Additional libraries may be added when technically justified.

Do not introduce a new framework simply because it is popular.

---

# 46. Coding Standards

Code should be:

- modular
- readable
- maintainable
- reasonably documented
- testable
- consistently structured

Avoid:

- giant files
- duplicated logic
- unnecessary abstractions
- hardcoded environment-specific values
- unused dependencies
- dead code

---

# 47. Development Strategy

Development should happen incrementally.

Recommended sequence:

    Phase 1
    Project foundation

    Phase 2
    Dataset pipeline

    Phase 3
    Centralized ML baseline

    Phase 4
    Four independent local models

    Phase 5
    Federated Learning + FedAvg

    Phase 6
    FL validation/audit

    Phase 7
    Non-IID experiments

    Phase 8
    Threat Intelligence

    Phase 9
    Node/Express backend

    Phase 10
    React dashboard

    Phase 11
    Docker integration

    Phase 12
    End-to-end integration

    Phase 13
    QA/testing

    Phase 14
    Documentation and final cleanup

Do not skip foundational validation merely to reach the UI faster.

---

# 48. Definition of Done

The project should be considered complete only when:

- 5G-NIDD data pipeline works
- four simulated operators exist
- local models work
- centralized baseline exists
- actual federated learning works
- FedAvg works
- multiple FL rounds work
- IID experiment works
- non-IID experiment works
- CTI generation works
- CTI propagation works
- backend APIs work
- MongoDB persistence works
- React dashboard displays actual system data
- Docker Compose starts the required services
- end-to-end workflow works
- tests pass
- actual experiment results are recorded
- documentation matches implementation
- known limitations are documented

---

# 49. Final Demonstration Scenario

The final demonstration should ideally show:

1. Start the Docker environment.
2. Show four operators.
3. Show their local data ownership.
4. Start federated training.
5. Show Global Model v1.
6. Show operators training locally.
7. Show model updates being exchanged.
8. Show FedAvg aggregation.
9. Show Global Model v2.
10. Repeat for several rounds.
11. Show model metrics.
12. Show an actual detected threat.
13. Generate CTI.
14. Propagate the CTI to participating operators.
15. Show the event on the React dashboard.
16. Show experiment results.
17. Compare centralized/local/federated performance.

The demonstration must reflect actual system behavior.

---

# 50. Limitations To Document

The final documentation should explicitly acknowledge limitations such as:

- operators are simulated rather than real telecom companies
- telecom traffic is represented by a public intrusion-detection dataset
- deployment is a local/containerized simulation
- federated learning does not by itself guarantee complete privacy
- real telecom regulatory compliance is outside the scope
- real-time telecom network integration is outside the scope
- production-scale threat intelligence infrastructure is outside the scope
- advanced privacy mechanisms are optional future work unless actually implemented

---

# 51. Future Extensions

Possible future work:

- Secure Aggregation
- Differential Privacy
- Homomorphic Encryption
- MPC
- STIX/TAXII interoperability
- stronger authentication
- Kubernetes deployment
- larger operator federation
- additional telecom datasets
- advanced deep-learning models
- real-time streaming
- online learning
- adversarial/federated poisoning detection
- explainable AI
- real telecom testbed integration

These are future extensions only unless explicitly implemented.

---

# 52. Absolute Rules for the AI Coding Agent

The coding agent MUST follow these rules:

1. Read this PROJECT_SPEC.md before making architectural decisions.
2. Read AGENTS.md if present.
3. Do not invent functionality.
4. Do not fabricate metrics.
5. Do not fabricate experiment results.
6. Do not claim a feature works until it has been tested.
7. Do not send raw operator data to the federated coordinator.
8. Do not replace real FL with fake aggregation.
9. Do not replace actual ML with hardcoded predictions.
10. Do not hardcode experimental metrics.
11. Do not create fake dashboard data for the final system.
12. Do not add unnecessary frameworks.
13. Do not rewrite working code without a technical reason.
14. Preserve working components when implementing new features.
15. Keep ML/FL code in Python.
16. Keep application API logic in Node/Express.
17. Keep frontend logic in React.
18. Use MongoDB for application persistence.
19. Use Docker for distributed environment simulation.
20. Keep the system runnable after each phase.
21. Test important changes.
22. Record actual experiment results.
23. Update IMPLEMENTATION_STATUS.md.
24. Update EXPERIMENT_LOG.md when an experiment is performed.
25. Clearly identify temporary mocks.
26. Clearly identify simulated telecom functionality.
27. Do not claim production readiness unless objectively justified.
28. Do not claim absolute privacy.
29. Do not proceed to a major subsequent phase when the current phase is broken unless explicitly instructed.
30. Prefer the smallest correct implementation over unnecessary complexity.

---

# 53. Agent Operating Principle

The AI coding agent is the implementation engineer.

The project architecture and requirements in this file are authoritative.

When a new task is provided:

1. Read this specification.
2. Inspect the existing repository.
3. Inspect IMPLEMENTATION_STATUS.md.
4. Understand what already works.
5. Make only the changes required for the requested phase.
6. Test the changes.
7. Report actual results.
8. Update status documentation.
9. Stop and wait for the next instruction.

Do not independently expand project scope.

---

# 54. Success Criteria

The project succeeds when it demonstrates, with actual executable software:

**Multiple simulated telecom operators can collaboratively improve a cybersecurity detection model through federated learning while retaining their raw training data locally, and detected threats can be represented and propagated as structured cyber threat intelligence through a centralized application/dashboard layer.**

The emphasis is on:

    REAL DATA
    REAL LOCAL TRAINING
    REAL FEDERATED LEARNING
    REAL FEDAVG
    REAL EXPERIMENTS
    REAL CTI
    REAL API INTEGRATION
    REAL DASHBOARD DATA
    REAL DOCKER DEPLOYMENT
    REPRODUCIBLE RESULTS

Not on fabricated demonstrations or excessive technology.
