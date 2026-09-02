export default function DiffViewer() {
  const brokenHCL = `resource "aws_s3_bucket" "app_assets" {
  bucket = "shadowplane_enterprise_assets_prod"
  # ERROR: Underscores are invalid in S3 bucket names
}

resource "aws_dynamodb_table" "agent_state" {
  name         = "ShadowPlane-Agent-State"
  billing_mode = "PROVISIONED"
  hash_key     = "LockID"
  # ERROR: Missing read_capacity and write_capacity

  attribute {
    name = "LockID"
    type = "S"
  }
}`;

  const patchedHCL = `resource "aws_s3_bucket" "app_assets" {
  bucket = "shadowplane-enterprise-assets-prod"
  # FIXED: Hyphens used instead of underscores
}

resource "aws_dynamodb_table" "agent_state" {
  name           = "ShadowPlane-Agent-State"
  billing_mode   = "PROVISIONED"
  hash_key       = "LockID"
  read_capacity  = 5
  write_capacity = 5

  attribute {
    name = "LockID"
    type = "S"
  }
}`;

  const telemetryLog = {
    timestamp: "2026-09-01T19:09:33.984Z",
    deployment_id: "2a480482-ad38-4d51-9994-309f62dd9f69",
    intercepted_error: {
      source: "localstack/stderr",
      code: "InvalidBucketName",
      message:
        "The specified bucket is not valid. Bucket names must be between 3 and 63 characters long, using only lowercase letters, numbers, and hyphens.",
      resource_addr: "aws_s3_bucket.app_assets",
    },
    fastmcp_trace: {
      tool_invoked: "clone_and_deploy",
      sandbox: "localstack-shadowplane:4566",
      ai_model_primary: "shadowpatch-engine-v1",
      ai_model_fallback: "shadowpatch-engine-v1-lite",
      model_used: "shadowpatch-engine-v1-lite",
      temperature: 0.1,
      patch_size_bytes: 665,
      result: "PATCHED",
    },
  };

  return (
    <section className="border-b border-stone-300">
      {/* Section Header */}
      <div className="border-b border-stone-300 px-6 py-6 md:px-12">
        <p className="text-[10px] tracking-[0.3em] text-stone-400 uppercase mb-2">
          Component B
        </p>
        <h2 className="text-xl md:text-2xl font-bold text-stone-900">
          Audit Trail
        </h2>
        <p className="text-xs text-stone-500 mt-1">
          Side-by-side diff of the AI-patched Terraform code and intercepted
          telemetry
        </p>
      </div>

      {/* Diff Panes */}
      <div className="grid grid-cols-1 md:grid-cols-2">
        {/* Left: Broken */}
        <div className="border-b md:border-b-0 md:border-r border-stone-300">
          <div className="border-b border-stone-300 px-4 py-2 flex items-center justify-between bg-red-50">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-red-600 inline-block" />
              <span className="text-[10px] tracking-[0.2em] font-semibold text-red-700 uppercase">
                main.tf — Before
              </span>
            </div>
            <span className="text-[10px] text-red-500 tracking-wider">
              FAILING
            </span>
          </div>
          <pre className="p-4 text-xs leading-relaxed text-stone-700 overflow-x-auto bg-white">
            {brokenHCL.split("\n").map((line, i) => (
              <div key={i} className="flex">
                <span className="w-8 shrink-0 text-stone-400 text-right pr-3 select-none border-r border-stone-200 mr-3">
                  {i + 1}
                </span>
                <span
                  className={
                    line.includes("ERROR") || line.includes("shadowplane_")
                      ? "text-red-700 bg-red-50 -mx-1 px-1"
                      : line.includes("PROVISIONED")
                      ? "text-red-700 bg-red-50 -mx-1 px-1"
                      : ""
                  }
                >
                  {line}
                </span>
              </div>
            ))}
          </pre>
        </div>

        {/* Right: Patched */}
        <div>
          <div className="border-b border-stone-300 px-4 py-2 flex items-center justify-between bg-green-50">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-green-700 inline-block" />
              <span className="text-[10px] tracking-[0.2em] font-semibold text-green-800 uppercase">
                main.tf — After (ShadowPatch Applied)
              </span>
            </div>
            <span className="text-[10px] text-green-600 tracking-wider">
              PASSING
            </span>
          </div>
          <pre className="p-4 text-xs leading-relaxed text-stone-700 overflow-x-auto bg-white">
            {patchedHCL.split("\n").map((line, i) => (
              <div key={i} className="flex">
                <span className="w-8 shrink-0 text-stone-400 text-right pr-3 select-none border-r border-stone-200 mr-3">
                  {i + 1}
                </span>
                <span
                  className={
                    line.includes("FIXED") ||
                    line.includes("shadowplane-enterprise")
                      ? "text-green-800 bg-green-50 -mx-1 px-1"
                      : line.includes("read_capacity") ||
                        line.includes("write_capacity")
                      ? "text-green-800 bg-green-50 -mx-1 px-1"
                      : ""
                  }
                >
                  {line}
                </span>
              </div>
            ))}
          </pre>
        </div>
      </div>

      {/* Bottom Pane: Telemetry */}
      <div className="border-t border-stone-300">
        <div className="border-b border-stone-300 px-4 py-2 flex items-center justify-between bg-stone-50">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-orange-600 inline-block" />
            <span className="text-[10px] tracking-[0.2em] font-semibold text-stone-600 uppercase">
              Telemetry · LocalStack stderr + FastMCP Trace
            </span>
          </div>
          <span className="text-[10px] text-orange-600 tracking-wider font-semibold">
            JSON
          </span>
        </div>
        <pre className="p-4 text-xs leading-relaxed text-stone-600 overflow-x-auto bg-white">
          {JSON.stringify(telemetryLog, null, 2)}
        </pre>
      </div>
    </section>
  );
}
