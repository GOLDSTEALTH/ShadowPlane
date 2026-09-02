export default function IntegrationMatrix() {
  // Adding explicit shadow glow colors for each technology to maintain premium depth
  const integrations = [
    { name: "GitHub Actions", icon: "🐙", glow: "shadow-[0_0_30px_rgba(59,130,246,0.15)]" },
    { name: "GitLab CI", icon: "🦊", glow: "shadow-[0_0_30px_rgba(249,115,22,0.15)]" },
    { name: "Jenkins", icon: "🕴️", glow: "shadow-[0_0_30px_rgba(239,68,68,0.15)]" },
    { name: "Terraform", icon: "🏗️", glow: "shadow-[0_0_30px_rgba(168,85,247,0.15)]" },
    { name: "OpenTofu", icon: "🧅", glow: "shadow-[0_0_30px_rgba(234,179,8,0.15)]" },
    { name: "Ansible", icon: "🅰️", glow: "shadow-[0_0_30px_rgba(220,38,38,0.15)]" },
    { name: "Checkov", icon: "🛡️", glow: "shadow-[0_0_30px_rgba(99,102,241,0.15)]" },
    { name: "Slack", icon: "💬", glow: "shadow-[0_0_30px_rgba(20,184,166,0.15)]" },
  ];

  return (
    <section className="py-24 border-t border-zinc-800/60 bg-zinc-950">
      <div className="max-w-6xl mx-auto px-6 text-center">
        <p className="text-[11px] text-cyan-500 font-mono font-semibold tracking-[0.3em] uppercase mb-4">
          Framework Agnostic
        </p>
        <h2 className="text-3xl md:text-4xl font-bold text-zinc-100 tracking-tight mb-16">
          Plugs into your existing pipeline in minutes.
        </h2>

        <div className="flex flex-wrap items-center justify-center gap-10 md:gap-16">
          {integrations.map((integration) => (
            <div
              key={integration.name}
              className="flex flex-col items-center gap-4 cursor-pointer group"
            >
              <div
                className={`flex items-center justify-center w-20 h-20 rounded-2xl bg-zinc-900 border border-zinc-800 transition-all duration-300 group-hover:scale-110 group-hover:-translate-y-1 ${integration.glow}`}
              >
                <span className="text-5xl drop-shadow-lg">{integration.icon}</span>
              </div>
              <span className="text-sm font-semibold text-zinc-400 group-hover:text-zinc-200 transition-colors">
                {integration.name}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
