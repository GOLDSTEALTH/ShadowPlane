export default function EngineeringSpecs() {
  const specs = [
    {
      icon: "🧠",
      header: "Bring-Your-Own-Model",
      body: "Native LiteLLM integration supports GPT-4o, Claude 3.5, Gemini 3.7, and Ollama for AI-assisted Terraform repair.",
      tag: "BYOM",
    },
    {
      icon: "🧊",
      header: "Two-Stage Pre-Warm Sandbox",
      body: "Safely simulates production state updates. Clones 'main' to build a mock environment, then applies your PR branch on top.",
      tag: "SAFE-STATE",
    },
    {
      icon: "🛡",
      header: "LocalStack Sandbox Isolation",
      body: "Terraform execution is redirected to a LocalStack container with mock credentials. Network egress controls are roadmapped.",
      tag: "SECURITY",
    },
    {
      icon: "🔒",
      header: "Circuit Breaker Safety",
      body: "Prevents runaway agent retry loops. After 4 consecutive failures, execution is hard-blocked until a human operator intervenes.",
      tag: "SAFETY",
    },
    {
      icon: "⚡",
      header: "CI/CD Integration",
      body: "Drop-in GitHub Actions support. Headless CLI with deterministic exit codes (0 = pass, 1 = fail) for any CI runner.",
      tag: "CI-CD",
    },
    {
      icon: "🔍",
      header: "Security Scanning",
      body: "Integrated Checkov static analysis with fail-closed enforcement. Missing scanner binary blocks the pipeline, not bypasses it.",
      tag: "SCANNING",
    },,
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
