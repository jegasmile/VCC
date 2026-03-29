#!/bin/bash
set -e

PROJECT_ID="mtech-ai-vcc"
ZONE="asia-south1-a"
INSTANCE_NAME="burst-vm-$(date +%Y%m%d-%H%M%S)"

gcloud compute instances create "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --machine-type=e2-medium \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --no-service-account \
  --no-scopes
