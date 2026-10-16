export default function EngineeringSpecs() {
  const specs = [
    {
      icon: "🛡",
      header: "Docker Container Sandboxing",
      body: "Terraform runs in an ephemeral, rootless Docker sandbox container with host credentials stripped and network egress restricted to LocalStack.",
      tag: "CONTAINMENT",
    },
    {
      icon: "🔍",
      header: "Change-Risk Intelligence",
      body: "Parses plan JSON to detect destructive stateful replacements (RDS, S3, KMS) and flags IAM privilege creep before apply.",
      tag: "CHANGE-RISK",
    },
    {
      icon: "📜",
      header: "Cryptographic Attestation",
      body: "Generates tamper-evident SHA-256 evidence hashes and Markdown attestation packs for PR compliance and CI merge gates.",
      tag: "ATTESTATION",
    },
    {
      icon: "🔒",
      header: "Circuit Breaker Safety",
      body: "Prevents runaway agent retry loops. After 4 consecutive failures, execution is hard-blocked until an authorized human resets it.",
      tag: "SAFETY",
    },
    {
      icon: "⚡",
      header: "CI/CD Integration",
      body: "Drop-in GitHub Actions support. Headless CLI with deterministic exit codes (0 = pass, 1 = fail) for any CI runner.",
      tag: "CI-CD",
    },
    {
      icon: "🚨",
      header: "Fail-Closed Scanning",
      body: "Integrated Checkov static analysis with fail-closed enforcement. Missing scanner binaries block the pipeline, never bypass it.",
      tag: "SCANNING",
    },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6">
      <div className="text-center mb-16">
        <p className="text-sm text-cyan-500 font-medium tracking-wide mb-3">
          Built for Production
        </p>
        <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
          Engineering Specifications
        </h2>
        <p className="mt-3 text-zinc-400 max-w-xl mx-auto">
          Enterprise architecture designed for DevOps teams who deploy at scale.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-px bg-zinc-800 border border-zinc-800 rounded-xl overflow-hidden">
        {specs.map((spec) => (
          <div
            key={spec.tag}
            className="bg-zinc-900 p-6 flex flex-col gap-4 hover:bg-zinc-800/60 transition-colors"
          >
            {/* Icon + Tag */}
            <div className="flex items-center justify-between">
              <span className="text-2xl">{spec.icon}</span>
              <span className="text-[10px] tracking-widest text-cyan-500 font-mono font-semibold">
                {spec.tag}
              </span>
            </div>

            {/* Header */}
            <h3 className="text-sm font-semibold text-zinc-100">
              {spec.header}
            </h3>

            {/* Body */}
            <p className="text-xs text-zinc-500 leading-relaxed flex-1">
              {spec.body}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
