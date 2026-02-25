# Milestone 4 Report: Microservices using Google Pub/Sub Communication

**Course:** SOFE4630U – Cloud Computing  
**Milestone:** 4 — Microservices with Google Pub/Sub  

---

## 1. GitHub Link (Design Part Scripts)

Design microservice scripts are included in this repository:
- [`filter_reading/main.py`](./filter_reading/main.py) — FilterReading microservice  
- [`convert_reading/main.py`](./convert_reading/main.py) — ConvertReading microservice  

Repository: https://github.com/MohammadYasserZaki/SOFE4630U-MS4

---

## 2. Design Part

### Overview

The design part implements the same smart meter data preprocessing pipeline from Milestone 3, but using **microservices** instead of a Dataflow job. A single Google Pub/Sub topic is used to route messages between services via message attribute filtering.

### Architecture

```
Smart Meter Producer
      |
      | publish (function="raw reading")
      v
[smartmeter Pub/Sub Topic]
      |
      v
FilterReading Service
 - Receives: function="raw reading"
 - Drops records with any None/missing values
 - Forwards: function="convert reading"
      |
      v
[smartmeter Pub/Sub Topic]
      |
      v
ConvertReading Service
 - Receives: function="convert reading"
 - Converts: P(kPa) → P(psi) = P(kPa) / 6.895
 - Converts: T(°C) → T(°F) = T(°C) × 1.8 + 32
 - Publishes: function="converted"
      |
      v
[BigQuery Subscription]
 - Automatically stores converted records in BigQuery
```

### Microservice Descriptions

#### FilterReading Microservice (`filter_reading/main.py`)
- **Subscription Filter:** `attributes.function="raw reading"`
- **Logic:** Checks if any of `pressure`, `temperature`, or `humidity` fields are `None`. If any field is missing/null, the record is dropped (not forwarded). Otherwise, the full record is forwarded.
- **Output:** Publishes messages with attribute `function="convert reading"` to the same topic.
- **No data storage required** (stateless).

#### ConvertReading Microservice (`convert_reading/main.py`)
- **Subscription Filter:** `attributes.function="convert reading"`
- **Logic:** Applies the following unit conversions:
  - Pressure: `P(psi) = P(kPa) / 6.895`
  - Temperature: `T(F) = T(C) × 1.8 + 32`
- **Output:** Publishes the converted reading with attribute `function="converted"` to the same topic.
- **No data storage required** (stateless).

#### BigQuery Subscription
A BigQuery subscription on the `election` topic automatically stores converted readings in a BigQuery table without any custom code — use the **BigQuery subscription** type in Pub/Sub.

---

## 3. Discussion: Dataflow vs. Microservices

### Comparison Table

| Aspect | Apache Beam / Dataflow | Microservices (Pub/Sub) |
|--------|----------------------|-------------------------|
| **Scalability** | Auto-scales workers based on data volume; managed by GCP | Each service scales independently (e.g., Kubernetes HPA) |
| **Latency** | Higher latency for batch; low latency for streaming | Event-driven; very low latency for individual message processing |
| **Complexity** | Unified pipeline; all logic in one codebase | Distributed; each service is independent |
| **Fault Tolerance** | Built-in retry/checkpointing via Dataflow runner | Pub/Sub guarantees at-least-once delivery; services must handle retries |
| **Language/Framework** | Python (Apache Beam SDK) | Any language; loosely coupled |
| **State Management** | Supports windowing, aggregation, and stateful transforms | Stateless by default; state requires external storage (Redis, DB) |
| **Cost** | Charged per Dataflow worker-hour | GKE (Kubernetes) costs + Pub/Sub message costs |
| **Monitoring** | Dataflow UI with job DAG visualization | GKE/Cloud Logging per service |
| **Deployment** | Single job deployment | Deploy each service independently |
| **Development Speed** | Faster for batch/streaming pipelines | More boilerplate per service |

### Advantages of Dataflow
1. **Unified streaming/batch model:** Apache Beam handles both batch and real-time streaming in a single API, making it easier to switch modes without rewriting logic.
2. **Built-in stateful processing:** Windowing and aggregation (e.g., sum readings per hour) are natively supported without external storage.
3. **Simpler ops:** One job to deploy, monitor, and manage via the Dataflow UI.
4. **Auto-scaling:** Automatically adjusts the number of workers based on data volume with no manual configuration.

### Disadvantages of Dataflow
1. **Tight coupling:** All logic is in one pipeline; changing one step requires redeploying the whole job.
2. **Higher latency for complex pipelines:** Batch windows introduce delays compared to pure event-driven processing.
3. **Language limitation:** Primarily Python/Java; SDK constraints on certain operations.
4. **Cost:** Dataflow workers are charged even when idle, whereas microservices on GKE can scale to zero.

### Advantages of Microservices
1. **Independent deployability:** Each service (filter, convert, etc.) can be deployed, updated, and scaled independently without affecting others.
2. **Technology flexibility:** Each service can use different languages or libraries.
3. **Event-driven reactivity:** Each service triggers immediately when a relevant message arrives, enabling very low latency.
4. **Resilience:** Failure in one service doesn't crash the whole pipeline; Pub/Sub buffers messages.
5. **Reusability:** Individual services can be reused across different pipelines or applications.

### Disadvantages of Microservices
1. **Operational complexity:** Managing many separate containers, deployments, and subscriptions requires more DevOps work.
2. **State management overhead:** Stateful operations (like deduplication in the voting logger) require external stores (Redis, DB), adding infrastructure.
3. **Debugging difficulty:** Distributed tracing across multiple services is harder than inspecting a single Dataflow job's DAG.
4. **Network overhead:** Every inter-service call goes through Pub/Sub, introducing message serialization costs.
5. **At-least-once delivery:** Pub/Sub may deliver duplicates; services must handle idempotency.

### Conclusion

**Dataflow** is better suited for **large-scale, stateful batch or streaming analytics pipelines** (e.g., windowed aggregation of smart meter readings over time). **Microservices** are better for **event-driven, loosely coupled systems** where individual components need to scale and evolve independently (e.g., the election voting system, where services have clearly separate domains: logging, recording, and voting).

For the smart meter preprocessing use case, both approaches work well. Dataflow simplifies stateful aggregations, while microservices offer more flexibility and better fit cloud-native, container-first architectures.

---

## 4. Demo Videos

- **Voting System (~3 min):** [Link to be recorded and added]
- **Design Part (~5 min):** [Link to be recorded and added]
