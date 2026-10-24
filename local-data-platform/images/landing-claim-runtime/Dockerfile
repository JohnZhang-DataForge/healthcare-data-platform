FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="healthcare-landing-claim"
LABEL org.opencontainers.image.description="Guarded S3 Landing batch claim and legacy-ledger exclusion"

RUN groupadd --gid 10001 hdp \
 && useradd --uid 10001 --gid 10001 --no-create-home hdp \
 && python -m pip install --no-cache-dir "psycopg[binary]==3.2.10" "boto3==1.40.40"
WORKDIR /opt/healthcare/landing_claim
COPY --chown=10001:10001 apps/landing_claim/batch_ledger.py .
COPY --chown=10001:10001 apps/landing_claim/claim_discovered_inventory.py .
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AWS_EC2_METADATA_DISABLED=true
USER 10001:10001
ENTRYPOINT ["python","/opt/healthcare/landing_claim/claim_discovered_inventory.py"]
