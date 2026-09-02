export default function TerminalDiff() {
  const brokenLines = [
    { text: `resource "aws_s3_bucket" "app_assets" {`, hl: false },
    { text: `  bucket = "shadowplane_enterprise_assets_prod"`, hl: true },
    { text: `  # ↑ InvalidBucketName: underscores are illegal`, hl: true },
    { text: `}`, hl: false },
    { text: ``, hl: false },
    { text: `resource "aws_dynamodb_table" "agent_state" {`, hl: false },
    { text: `  name         = "ShadowPlane-Agent-State"`, hl: false },
    { text: `  billing_mode = "PROVISIONED"`, hl: true },
    { text: `  hash_key     = "LockID"`, hl: false },
    { text: `  # ↑ Missing read_capacity / write_capacity`, hl: true },
    { text: ``, hl: false },
    { text: `  attribute {`, hl: false },
    { text: `    name = "LockID"`, hl: false },
    { text: `    type = "S"`, hl: false },
    { text: `  }`, hl: false },
    { text: `}`, hl: false },
  ];

  const patchedLines = [
    { text: `resource "aws_s3_bucket" "app_assets" {`, hl: false },
    { text: `  bucket = "shadowplane-enterprise-assets-prod"`, hl: true },
    { text: `  # ✓ Hyphens used — bucket name now valid`, hl: true },
    { text: `}`, hl: false },
    { text: ``, hl: false },
    { text: `resource "aws_dynamodb_table" "agent_state" {`, hl: false },
    { text: `  name           = "ShadowPlane-Agent-State"`, hl: false },
    { text: `  billing_mode   = "PROVISIONED"`, hl: false },
    { text: `  hash_key       = "LockID"`, hl: false },
    { text: `  read_capacity  = 5`, hl: true },
    { text: `  write_capacity = 5`, hl: true },
    { text: `  attribute {`, hl: false },
    { text: `    name = "LockID"`, hl: false },
    { text: `    type = "S"`, hl: false },
    { text: `  }`, hl: false },
    { text: `}`, hl: false },
  ];

  return (
    <div className="w-full max-w-5xl mx-auto">
      {/* Window Chrome */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 shadow-2xl shadow-black/50 backdrop-blur-sm overflow-hidden">
        {/* Title Bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800 bg-zinc-900">
          {/* Traffic lights */}
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500/80" />
            <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
            <span className="w-3 h-3 rounded-full bg-green-500/80" />
          </div>
          <span className="text-xs text-zinc-500 font-mono ml-2">
            shadowplane — main.tf diff
          </span>
          <div className="flex-1" />
          <span className="text-[10px] text-cyan-500 font-mono tracking-wider">
            GEMINI 3.6-FLASH PATCH
          </span>
        </div>

        {/* Diff Panes */}
        <div className="grid grid-cols-1 md:grid-cols-2 font-mono text-[13px] leading-6">
          {/* Left: Broken */}
          <div className="md:border-r border-zinc-800">
            <div className="px-4 py-2 border-b border-zinc-800/60 bg-zinc-900/60">
              <span className="text-[10px] tracking-widest uppercase text-red-400 font-semibold">
                ✕ Before — Failing
              </span>
            </div>
            <div className="overflow-x-auto">
              {brokenLines.map((line, i) => (
                <div
                  key={i}
                  className={`flex px-4 ${
                    line.hl
                      ? "bg-red-500/10 border-l-2 border-red-500"
                      : "border-l-2 border-transparent"
                  }`}
                >
                  <span className="w-8 shrink-0 text-zinc-600 text-right pr-4 select-none">
                    {i + 1}
                  </span>
                  <span
                    className={
                      line.hl ? "text-red-300" : "text-zinc-400"
                    }
                  >
                    {line.text || "\u00A0"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Patched */}
          <div>
            <div className="px-4 py-2 border-b border-zinc-800/60 bg-zinc-900/60">
              <span className="text-[10px] tracking-widest uppercase text-emerald-400 font-semibold">
                ✓ After — Passing
              </span>
            </div>
            <div className="overflow-x-auto">
              {patchedLines.map((line, i) => (
                <div
                  key={i}
                  className={`flex px-4 ${
                    line.hl
                      ? "bg-emerald-500/10 border-l-2 border-emerald-500"
                      : "border-l-2 border-transparent"
                  }`}
                >
                  <span className="w-8 shrink-0 text-zinc-600 text-right pr-4 select-none">
                    {i + 1}
                  </span>
                  <span
                    className={
                      line.hl ? "text-emerald-300" : "text-zinc-400"
                    }
                  >
                    {line.text || "\u00A0"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom Status Bar */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-zinc-800 bg-zinc-900/60 text-[10px] text-zinc-500 font-mono">
          <span>deployment_id: 2a480482-ad38</span>
          <span className="text-emerald-500">● sys.exit(0) — Pipeline GREEN</span>
        </div>
      </div>
    </div>
  );
}
