import json
import time

import boto3


def create_static_site(domain: str) -> None:
    """Create a static site on S3."""
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=domain)
    s3.put_bucket_website(
        Bucket=domain,
        WebsiteConfiguration={
            "ErrorDocument": {"Key": "index.html"},
            "IndexDocument": {"Suffix": "index.html"},
        },
    )
    # Hello world index.html
    s3.put_object(
        Bucket=domain,
        Key="index.html",
        Body=b"<p>Hello, world!</p>",
        ContentType="text/html",
    )
    s3.put_public_access_block(
        Bucket=domain,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{domain}/*"],
            }
        ],
    }
    s3.put_bucket_policy(Bucket=domain, Policy=json.dumps(bucket_policy, indent=2))

    # Get certificate
    acm = boto3.client("acm", region_name="us-east-1")
    response = acm.list_certificates()
    certificate = next(
        cert
        for cert in response["CertificateSummaryList"]
        if domain in cert["DomainName"]
    )
    certificate_arn = certificate["CertificateArn"]

    # CloudFront
    cloudfront = boto3.client("cloudfront")
    cloudfront.create_distribution(
        DistributionConfig={
            "CallerReference": domain,
            "Aliases": {"Quantity": 1, "Items": [domain]},
            "DefaultRootObject": "index.html",
            "Origins": {
                "Quantity": 1,
                "Items": [
                    {
                        "Id": domain,
                        "DomainName": f"{domain}.s3.us-east-1.amazonaws.com",
                        "S3OriginConfig": {"OriginAccessIdentity": ""},
                    }
                ],
            },
            "DefaultCacheBehavior": {
                "TargetOriginId": domain,
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                "ForwardedValues": {
                    "QueryString": False,
                    "Cookies": {"Forward": "none"},
                },
                "MinTTL": 0,
            },
            "Comment": "",
            "CallerReference": str(time.time()),
            "PriceClass": "PriceClass_100",
            "WebACLId": "",
            "Enabled": True,
            "ViewerCertificate": {
                "ACMCertificateArn": certificate_arn,
                "CloudFrontDefaultCertificate": False,
                "SSLSupportMethod": "sni-only",
            },
        }
    )
