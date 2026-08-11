# ShadowPlane Demo Infrastructure
# Provisions an S3 bucket and an IAM bucket policy.
#
# INTENTIONAL ERROR: S3 bucket names must be lowercase.
# "shadowplane-DEMO-INVALID" violates this rule, causing LocalStack to return:
#   api error InvalidBucketName: The specified bucket is not valid.
#
# demo_loop.py will detect this error, patch the bucket name to
# "shadowplane-demo-6401bb" (valid), and re-deploy successfully.
# Run ID: 6401bb

resource "aws_s3_bucket" "shadowplane_bucket" {
  # FATAL ERROR: uppercase letters are not allowed in S3 bucket names
  bucket = "shadowplane-DEMO-INVALID"
}

resource "aws_s3_bucket_policy" "shadowplane_policy" {
  bucket = aws_s3_bucket.shadowplane_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ShadowPlaneReadWrite"
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.shadowplane_bucket.arn}/*"
      }
    ]
  })
}
