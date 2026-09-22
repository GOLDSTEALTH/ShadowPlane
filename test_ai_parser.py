import unittest
from engine.ai import extract_hcl

class TestAIParser(unittest.TestCase):
    def test_pure_hcl(self):
        hcl = 'resource "aws_s3_bucket" "test" {\n  bucket = "clean"\n}'
        self.assertEqual(extract_hcl(hcl).strip(), hcl)

    def test_markdown_hcl(self):
        raw = 'Here is the fixed code:\n```hcl\nresource "aws_s3_bucket" "test" {\n  bucket = "fixed"\n}\n```\nHope this helps!'
        expected = 'resource "aws_s3_bucket" "test" {\n  bucket = "fixed"\n}'
        self.assertEqual(extract_hcl(raw).strip(), expected)

    def test_markdown_generic(self):
        raw = '```\nresource "aws_s3_bucket" "test" {}\n```'
        expected = 'resource "aws_s3_bucket" "test" {}'
        self.assertEqual(extract_hcl(raw).strip(), expected)

    def test_xml_claude_style(self):
        raw = "I found the error. The bucket name cannot contain uppercase letters.\n\n<fixed_code>\nresource \"aws_s3_bucket\" \"test\" {\n  bucket = \"lowercase\"\n}\n</fixed_code>"
        expected = 'resource "aws_s3_bucket" "test" {\n  bucket = "lowercase"\n}'
        self.assertEqual(extract_hcl(raw).strip(), expected)

    def test_bare_backticks_no_newlines(self):
        raw = '```hcl resource "aws_s3_bucket" "test" {} ```'
        # Our regex strips leading ```hcl and trailing ``` if no newlines exist 
        expected = 'resource "aws_s3_bucket" "test" {}'
        self.assertEqual(extract_hcl(raw).strip(), expected)

if __name__ == '__main__':
    unittest.main()
