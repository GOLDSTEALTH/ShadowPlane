import asyncio
import time
import os
from dotenv import load_dotenv
from engine.ai import repair_terraform_code

# Prevent massive logging output
import logging
logging.getLogger().setLevel(logging.ERROR)

load_dotenv()

TEST_CASES = [
    {
        "name": "Invalid S3 Bucket Name",
        "error": "api error InvalidBucketName: The specified bucket is not valid.",
        "hcl": 'resource "aws_s3_bucket" "b" { bucket = "MY_INVALID_BUCKET_NAME" }'
    },
    {
        "name": "Unsupported EC2 Instance Type",
        "error": "api error InvalidParameterValue: The requested instance type t2.supermicro is not supported in your requested Availability Zone.",
        "hcl": 'resource "aws_instance" "web" { ami = "ami-123456" \n instance_type = "t2.supermicro" }'
    },
    {
        "name": "IAM Policy Missing Resource",
        "error": "api error MalformedPolicyDocument: Syntax errors in policy. Missing required field Resource.",
        "hcl": 'resource "aws_iam_policy" "p" { policy = jsonencode({ Version = "2012-10-17", Statement = [{ Action = ["s3:ListBucket"], Effect = "Allow" }] }) }'
    },
    {
        "name": "DynamoDB Missing Hash Key",
        "error": "api error ValidationException: No Hash Key specified in schema.",
        "hcl": 'resource "aws_dynamodb_table" "t" { name = "my-table" \n billing_mode = "PAY_PER_REQUEST" \n attribute { name = "id" \n type = "S" } }'
    },
    {
        "name": "Security Group Invalid CIDR",
        "error": "api error InvalidParameterValue: The CIDR block '10.0.0.256/24' is malformed.",
        "hcl": 'resource "aws_security_group_rule" "r" { type = "ingress" \n from_port = 80 \n to_port = 80 \n protocol = "tcp" \n cidr_blocks = ["10.0.0.256/24"] \n security_group_id = "sg-123" }'
    }
]

async def run_benchmark():
    print("Starting ShadowPlane AST Parser Load Test...")
    print(f"Running {len(TEST_CASES)} simulated infrastructure failures against the live LLM API.")
    print("-" * 60)
    
    results = []
    
    # We will use the model specified in the environment or default to gemini/gemini-3.7-flash for speed
    model = os.getenv("AI_MODEL", "gemini/gemini-3.7-flash")
    
    for i, test in enumerate(TEST_CASES):
        print(f"[{i+1}/{len(TEST_CASES)}] Testing: {test['name']}...", end="", flush=True)
        
        start_time = time.time()
        try:
            patched_hcl = await repair_terraform_code(
                model=model,
                base_url=None,
                error_text=test["error"],
                current_hcl=test["hcl"]
            )
            latency = time.time() - start_time
            
            # Verify the parser successfully stripped out any markdown/XML
            is_clean = "```" not in patched_hcl and "<" not in patched_hcl[:5]
            has_content = len(patched_hcl.strip()) > 10
            success = is_clean and has_content
            
            results.append({
                "name": test["name"],
                "success": success,
                "latency": latency,
                "clean_hcl": is_clean
            })
            print(f" Done ({latency:.2f}s) - {'SUCCESS' if success else 'FAILED'}")
            
        except Exception as e:
            latency = time.time() - start_time
            results.append({
                "name": test["name"],
                "success": False,
                "latency": latency,
                "clean_hcl": False
            })
            print(f" FAILED ({str(e)})")
            
    print("-" * 60)
    print("BENCHMARK COMPLETE")
    print("-" * 60)
    print(f"| {'Test Case':<30} | {'Success':<8} | {'Latency':<8} | {'Clean HCL':<9} |")
    print(f"|{'-'*32}|{'-'*10}|{'-'*10}|{'-'*11}|")
    
    total_success = 0
    total_latency = 0
    
    for r in results:
        success_str = "PASS" if r["success"] else "FAIL"
        clean_str = "YES" if r["clean_hcl"] else "NO"
        print(f"| {r['name']:<30} | {success_str:<8} | {r['latency']:>6.2f}s | {clean_str:<9} |")
        
        if r["success"]: total_success += 1
        total_latency += r["latency"]
        
    avg_latency = total_latency / len(TEST_CASES) if TEST_CASES else 0
    success_rate = (total_success / len(TEST_CASES)) * 100
    
    print("-" * 60)
    print(f"Total Success Rate: {success_rate:.1f}%")
    print(f"Average Latency:    {avg_latency:.2f} seconds")
    print("-" * 60)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
