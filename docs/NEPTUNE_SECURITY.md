# Amazon Neptune Security Guide

This guide covers the target AWS deployment for OntoForge exports.

## Network

* Deploy Amazon Neptune in private subnets.
* Restrict security group inbound access to the application tier on port `8182`.
* Use VPC endpoints for Amazon S3 where Bulk Loader files are staged.
* Enable VPC Flow Logs for the VPC or relevant subnets.

Metric: zero public internet exposure for Neptune.

## Encryption

* Enable Neptune storage encryption with an AWS KMS customer-managed key.
* Require TLS 1.2 or later for application connections.
* Use S3 SSE-KMS for Bulk Loader source files.
* Enable S3 Block Public Access.
* Add a bucket policy that denies non-TLS requests:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyInsecureTransport",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": [
      "arn:aws:s3:::example-bucket",
      "arn:aws:s3:::example-bucket/ontoforge/*"
    ],
    "Condition": {"Bool": {"aws:SecureTransport": "false"}}
  }]
}
```

Metric: 100% of graph data encrypted at rest and in transit.

## IAM for Bulk Loader

Scope S3 access to the exact bucket and prefix:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example-bucket",
      "Condition": {"StringLike": {"s3:prefix": "ontoforge/*"}}
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::example-bucket/ontoforge/*"
    }
  ]
}
```

Trust Neptune to assume the loader role:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "neptune.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

## IAM for Query Execution

Use separate roles for read-only and write operations:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "neptune-db:ReadDataViaQuery",
      "neptune-db:WriteDataViaQuery"
    ],
    "Resource": "arn:aws:neptune-db:ap-northeast-2:123456789012:cluster-resource-id/*"
  }]
}
```

Metric: zero `Resource: "*"` statements for Neptune data-plane access.

## Logging

* Enable Neptune audit logs to Amazon CloudWatch Logs.
* Log loader job starts and status checks.
* Alert on unexpected write queries, repeated failed auth, and loader failures.
