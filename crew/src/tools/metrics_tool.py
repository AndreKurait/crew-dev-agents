import json
import os
from datetime import datetime, timezone

import boto3
from crewai.tools import tool


def _get_s3():
    return boto3.client("s3", region_name=os.environ.get("BEDROCK_REGION", "us-west-2"))


def _bucket():
    return os.environ.get("METRICS_BUCKET", "crew-dev-agents-artifacts")


@tool("store_metrics")
def store_metrics(metrics: str) -> str:
    """Store crew run metrics as JSON to S3. Input is a JSON string."""
    try:
        s3 = _get_s3()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
        key = f"metrics/{ts}.json"
        s3.put_object(Bucket=_bucket(), Key=key, Body=metrics, ContentType="application/json")
        return json.dumps({"bucket": _bucket(), "key": key})
    except Exception as e:
        return f"Error storing metrics: {e}"


@tool("read_recent_metrics")
def read_recent_metrics(count: int = 5) -> str:
    """Read the most recent N metric files from S3."""
    try:
        s3 = _get_s3()
        resp = s3.list_objects_v2(Bucket=_bucket(), Prefix="metrics/", MaxKeys=100)
        objects = sorted(resp.get("Contents", []), key=lambda o: o["Key"], reverse=True)[:int(count)]
        if not objects:
            return "No metrics found yet."
        results = []
        for obj in objects:
            body = s3.get_object(Bucket=_bucket(), Key=obj["Key"])["Body"].read()
            results.append(json.loads(body))
        return json.dumps(results)
    except Exception as e:
        return f"Error reading metrics: {e}"
