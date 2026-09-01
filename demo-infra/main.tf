# ShadowPlane Demo Infrastructure
# Provisions an S3 bucket and an IAM bucket policy.

resource "aws_s3_bucket" "shadowplane_bucket" {
  bucket = "shadowplane-demo-862e61"
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
