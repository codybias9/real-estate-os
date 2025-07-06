import argparse
import json
import os
import random
from urllib.parse import urlparse

try:
    import boto3
except ImportError:
    boto3 = None

def load_data(uri: str) -> dict:
    parsed_uri = urlparse(uri)
    scheme = parsed_uri.scheme
    if scheme == "s3":
        if not boto3:
            raise ImportError("boto3 is required for S3 support. Please install it with 'pip install boto3'.")
        s3 = boto3.client("s3")
        bucket = parsed_uri.netloc
        key = parsed_uri.path.lstrip("/")
        response = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
    elif scheme == "file" or not scheme:
        path = parsed_uri.path or uri
        if os.name == "nt" and path.startswith("/"):
            path = path[1:]
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported URI scheme: {scheme}")

def write_data(data: dict, uri: str):
    parsed_uri = urlparse(uri)
    scheme = parsed_uri.scheme
    output_content = json.dumps(data, indent=2)

    if scheme == "s3":
        if not boto3:
            raise ImportError("boto3 is required for S3 support. Please install it with 'pip install boto3'.")
        s3 = boto3.client("s3")
        bucket = parsed_uri.netloc
        key = parsed_uri.path.lstrip("/")
        s3.put_object(Bucket=bucket, Key=key, Body=output_content.encode("utf-8"))
        print(f"Successfully wrote enriched data to s3://{bucket}/{key}")
    elif scheme == "file" or not scheme:
        path = parsed_uri.path or uri
        if os.name == "nt" and path.startswith("/"):
            path = path[1:]
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(output_content)
        print(f"Successfully wrote enriched data to {path}")
    else:
        raise ValueError(f"Unsupported URI scheme: {scheme}")

def enrich_with_fake_assessor_data(property_data: dict) -> dict:
    enriched_data = property_data.copy()
    enriched_data["assessor_data"] = {
        "apn": f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(10, 99)}",
        "square_footage": random.randint(1200, 4500),
        "bedrooms": random.randint(2, 6),
        "bathrooms": round(random.uniform(1.0, 4.5), 1),
        "year_built": random.randint(1950, 2023),
        "assessed_value": random.randint(250000, 1500000),
    }
    print("Enriched property with fake assessor data.")
    return enriched_data

def main():
    parser = argparse.ArgumentParser(description="Enrich property data.")
    parser.add_argument("--input-uri", required=True, help="Input URI (local or s3://).")
    parser.add_argument("--output-uri", required=True, help="Output URI (local or s3://).")
    args = parser.parse_args()
    property_data = load_data(args.input_uri)
    enriched_data = enrich_with_fake_assessor_data(property_data)
    write_data(enriched_data, args.output_uri)

if __name__ == "__main__":
    main()
