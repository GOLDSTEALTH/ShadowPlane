export default function EngineeringSpecs() {
  const specs = [
    {
      id: "isolation",
      header: "Zero-Trust Isolation",
      code: "NETWORK_EGRESS=DENY_ALL",
      body: "Shared-kernel Docker MVP transitioning to Firecracker microVMs. Strict zero network egress to live AWS environments.",
      tag: "SECURITY",
    },
    {
      id: "guardrails",
      header: "Token Guardrails",
      code: "MCP_SCOPE=*.tf ONLY",
      body: "Agent rigidly scoped via MCP to parse only .tf files. Physically blocked from scanning state files or large .terraform directories.",
      tag: "POLICY",
    },
    {
      id: "latency",
      header: "Latency & Fallbacks",
      code: "COLD_START<100ms",
      body: "Sub-100ms cold starts via Warm Pools. Dynamic model degradation (Gemini 3.7 to 3.6) ensures pipeline resiliency during API spikes.",
      tag: "PERF",
    },
    {
      id: "escape",
      header: "The Escape Hatch",
      code: "HUMAN_GATE=REQUIRED",
      body: 'Mandatory human review gates for destructive operations (terraform destroy). Direct webhook bypass if the interception gateway goes down.',
      tag: "SAFETY",
    },
  ];

  return (
    <section className="border-b border-stone-300">
      {/* Section Header */}
      <div className="border-b border-stone-300 px-6 py-6 md:px-12">
        <p className="text-[10px] tracking-[0.3em] text-stone-400 uppercase mb-2">
          Component C
        </p>
        <h2 className="text-xl md:text-2xl font-bold text-stone-900">
          Engineering Specifications
        </h2>
        <p className="text-xs text-stone-500 mt-1">
          Enterprise architecture data sheet — for DevOps veterans who read
          RFCs, not marketing copy
        </p>
      </div>

      {/* 4-Column Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
        {specs.map((spec, i) => (
          <div
            key={spec.id}
            className={`
              border-b sm:border-b xl:border-b-0 border-stone-300 p-5
              ${i < specs.length - 1 ? "sm:border-r xl:border-r" : ""}
              ${i === 0 ? "" : ""}
            `}
          >
            {/* Tag */}
            <div className="flex items-center justify-between mb-3">
              <span className="text-[9px] tracking-[0.3em] font-bold text-orange-600 uppercase border border-orange-600 px-2 py-0.5">
                {spec.tag}
              </span>
              <span className="text-[9px] tracking-wider text-stone-400">
                SPEC-{String(i + 1).padStart(2, "0")}
              </span>
            </div>

            {/* Header */}
            <h3 className="text-sm font-bold text-stone-900 mb-2">
              {spec.header}
            </h3>

            {/* Code line */}
            <div className="border border-stone-300 bg-stone-50 px-3 py-1.5 mb-3">
              <code className="text-[10px] text-orange-700 font-bold">
                {spec.code}
              </code>
            </div>

            {/* Body */}
            <p className="text-xs text-stone-600 leading-relaxed">
              {spec.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
