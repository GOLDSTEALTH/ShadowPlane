export default function EngineeringSpecs() {
  const specs = [
    {
      icon: "🛡",
      header: "Zero-Trust Isolation",
      body: "Shared-kernel Docker MVP transitioning to Firecracker microVMs. Strict zero network egress to live AWS environments.",
      tag: "SECURITY",
    },
    {
      icon: "🔒",
      header: "Token Guardrails",
      body: "Agent rigidly scoped via MCP to parse only .tf files. Physically blocked from scanning state files or large .terraform directories.",
      tag: "POLICY",
    },
    {
      icon: "⚡",
      header: "Latency & Fallbacks",
      body: "Sub-100ms cold starts via Warm Pools. Intelligent ShadowPatch fallback routing ensures pipeline resiliency during API spikes.",
      tag: "PERFORMANCE",
    },
    {
      icon: "🚨",
      header: "The Escape Hatch",
      body: "Mandatory human review gates for destructive operations (terraform destroy). Direct webhook bypass if the interception gateway goes down.",
      tag: "SAFETY",
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
