# Milestone 4: Microservices using Google Pub/Sub Communication

## Overview

This project implements a cloud-based election system using microservices that communicate through a single **Google Pub/Sub topic**. The system uses **event-driven architecture** with message attribute filtering so each service only receives the messages relevant to it.

### GCP Project: `myride-478722`

---

## Architecture

```
Voting Machine (Local)
        |
        | publish (function="submit vote")
        v
  [election Pub/Sub Topic]
        |
   +----+----+
   |         |
   v         v
Logger    (filters function="submit vote")
Service   
(GKE+Redis)
   |
   | publish (function="record vote")  OR  publish (function="result", machineID=X)
   v
  [election Pub/Sub Topic]
        |
   +----+----+
   |         |
   v         v
Recorder  Voting Machine subscription
Service   (filters function="result" AND machineID=X)
(GKE+PG)
   |
   | publish (function="result", machineID=X)
   v
  [election Pub/Sub Topic]
```

---

## Project Structure

```
Cloud-computing-milestone4/
├── voting_logger/
│   ├── main.py          # Logger service (Python)
│   ├── Dockerfile       # Container definition
│   └── logger.yaml      # Kubernetes deployment (logger + Redis)
├── voting_record/
│   ├── main.py          # Recorder service (Python)
│   ├── Dockerfile       # Container definition
│   ├── recorder.yaml    # Kubernetes deployment (recorder + PostgreSQL)
│   └── postgres/
│       ├── CreateTable.sql  # DB schema
│       └── Dockerfile       # Custom PostgreSQL image
├── voting_machine/
│   └── main.py          # Local voting simulator script
├── filter_reading/      # Design Part: FilterReading microservice
│   ├── main.py
│   └── Dockerfile
├── convert_reading/     # Design Part: ConvertReading microservice
│   ├── main.py
│   └── Dockerfile
├── README.md
└── report.md
```

---

## GCP Setup (Prerequisites)

### 1. Pub/Sub Topic
A topic named `election` has been created in project `myride-478722` with a default subscription.

### 2. Service Account
- Service Account: `pubsub-admin@myride-478722.iam.gserviceaccount.com`
- Role: `Pub/Sub Admin`
- JSON key file downloaded to your local machine (copy it to each service folder before building/running)

### 3. Artifact Registry
- Repository: `sofe4630u`
- Type: Docker
- Region: `northamerica-northeast2` (Toronto)
- Full path: `northamerica-northeast2-docker.pkg.dev/myride-478722/sofe4630u`

---

## Deployment Steps (in GCP Cloud Shell)

### Step 1: Clone the repo and configure environment

```bash
cd ~
git clone https://github.com/GeorgeDaoud3/SOFE4630U-MS4.git

# Set environment variables
REPO=northamerica-northeast2-docker.pkg.dev/myride-478722/sofe4630u
LOGGER_IMAGE=$REPO/logger
RECORDER_IMAGE=$REPO/recorder
POSTGRES_IMAGE=$REPO/postgres:election
PROJECT=$(gcloud config list project --format "value(core.project)")

echo "REPO: $REPO"
echo "PROJECT: $PROJECT"
```

### Step 2: Copy your JSON credential file

```bash
# Copy the downloaded JSON key to each service folder
cp ~/Downloads/myride-478722-*.json ~/SOFE4630U-MS4/voting_logger/
cp ~/Downloads/myride-478722-*.json ~/SOFE4630U-MS4/voting_record/
```

### Step 3: Build and deploy the Logger Service + Redis

```bash
# Build Docker image
cd ~/SOFE4630U-MS4/voting_logger
docker build . -t $LOGGER_IMAGE

# Push to Artifact Registry
docker push $LOGGER_IMAGE
# If refused, try: gcloud builds submit --tag $LOGGER_IMAGE

# Deploy to GKE
PROJECT=$PROJECT LOGGER_IMAGE=$LOGGER_IMAGE envsubst < logger.yaml | kubectl apply -f -

# Verify
kubectl get pods
kubectl logs <logger-pod-name>
```

### Step 4: Build and deploy the Recorder Service + PostgreSQL

```bash
# Build and push recorder image
cd ~/SOFE4630U-MS4/voting_record
gcloud builds submit -t $RECORDER_IMAGE

# Build and push postgres image
cd ~/SOFE4630U-MS4/voting_record/postgres
gcloud builds submit -t $POSTGRES_IMAGE

# Deploy to GKE
cd ~/SOFE4630U-MS4/voting_record
POSTGRES_IMAGE=$POSTGRES_IMAGE PROJECT=$PROJECT RECORDER_IMAGE=$RECORDER_IMAGE envsubst < recorder.yaml | kubectl apply -f -

# Verify
kubectl get pods
kubectl logs <recorder-pod-name>
```

---

## Running the Voting Machine (Local)

```bash
# Install dependencies
pip install google-cloud-pubsub

# Place your JSON key in the voting_machine/ directory
cd voting_machine
python main.py
# Enter election ID: 1
# Enter machine ID: 1
```

Expected output:
- `"successful"` — vote was recorded
- `"Already Voted!!!"` — duplicate voter ID detected
- `"Time out"` — no response within 10 seconds

---

## Design Part: Smart Meter Microservices

See [`report.md`](./report.md) for the full design explanation and Dataflow vs Microservices discussion.

### FilterReading Service
- Subscribes with `function="raw reading"`
- Drops records with any `None` measurement field
- Forwards valid records with `function="convert reading"`

### ConvertReading Service  
- Subscribes with `function="convert reading"`
- Converts: `P(psi) = P(kPa) / 6.895`
- Converts: `T(F) = T(C) * 1.8 + 32`
- Publishes converted reading with `function="converted"`

### BigQuery Subscription
A BigQuery subscription should be added to the topic to automatically store converted results. In GCP Console:
- Go to Pub/Sub → Topic `election` → Subscriptions → Create Subscription
- Type: BigQuery
- BigQuery table: `myride-478722.smartmeter.converted_readings`

---

## GitHub Repository

Design part scripts: https://github.com/MohammadYasserZaki/SOFE4630U-MS4
