export default function IntegrationMatrix() {
  const integrations = [
    { name: "GitHub Actions", icon: "🐙" },
    { name: "Jenkins", icon: "🕴️" },
    { name: "GitLab CI", icon: "🦊" },
    { name: "Terraform Cloud", icon: "☁️" },
  ];

  return (
    <section className="py-24 border-t border-zinc-800/60 bg-zinc-950">
      <div className="max-w-6xl mx-auto px-6 text-center">
        <p className="text-[11px] text-cyan-500 font-mono font-semibold tracking-[0.3em] uppercase mb-4">
          Framework Agnostic
        </p>
        <h2 className="text-3xl md:text-4xl font-bold text-zinc-100 tracking-tight mb-12">
          Plugs into your existing pipeline in minutes.
        </h2>

        <div className="flex flex-wrap items-center justify-center gap-8 md:gap-16">
          {integrations.map((integration) => (
            <div
              key={integration.name}
              className="flex items-center gap-3 grayscale opacity-50 hover:grayscale-0 hover:opacity-100 transition-all duration-300 cursor-pointer"
            >
              <span className="text-3xl grayscale-0">{integration.icon}</span>
              <span className="text-lg font-semibold text-zinc-300">
                {integration.name}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
