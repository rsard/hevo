#!/usr/bin/env bash
# Pulls the latest image for this server and restarts the stack.
# Runs on the EC2 instance itself, from /opt/hevo — triggered over SSH by
# .github/workflows/deploy.yml, or by hand for a manual redeploy.
set -euo pipefail

cd /opt/hevo

set -a
source .env
set +a

# .env's AWS_ACCESS_KEY_ID/SECRET are the app's S3-only creds — unset them
# so this call falls back to the instance's IAM role (ECR pull permission).
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY

aws ecr get-login-password --region us-east-2 \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

docker compose pull
docker compose run --rm web python manage.py migrate --noinput
docker compose up -d
docker image prune -f
