#!/bin/bash
# Wait for MinIO server to start
until /usr/bin/mc alias set minio http://minio:9000 minioadmin minioadmin; do
  echo 'Waiting for MinIO server...'
  sleep 2
done

# Check if the bucket exists, create it only if it doesn't
if ! /usr/bin/mc ls minio/frames > /dev/null 2>&1; then
  /usr/bin/mc mb minio/frames
fi

# Set public policy for the frames bucket
/usr/bin/mc anonymous set public minio/frames