export default function BusinessROI() {
  const stats = [
    {
      id: "mttr",
      value: "45m → 12s",
      subtitle: "Mean Time to Recovery (MTTR)",
      detail:
        "Turn manual multi-engineer debugging sessions into an automated pipeline blip.",
    },
    {
      id: "blast",
      value: "100%",
      subtitle: "Blast Radius Containment",
      detail:
        "Invalid cloud configurations are physically prevented from reaching live AWS environments.",
    },
    {
      id: "footprint",
      value: "Zero",
      subtitle: "Production Agent Footprint",
      detail:
        "Operates entirely via webhooks and localized Docker/LocalStack sandboxes.",
    },
  ];

  return (
    <section className="py-24 border-t border-zinc-800/60 bg-zinc-950 relative overflow-hidden">
      {/* Subtle background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-cyan-500/5 rounded-[100%] blur-[120px] pointer-events-none" />

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-zinc-100 tracking-tight">
            The Business ROI
          </h2>
          <p className="mt-4 text-zinc-400 max-w-2xl mx-auto text-lg">
            Built for CTOs and Platform Leads who need undeniable reliability.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {stats.map((stat) => (
            <div
              key={stat.id}
              className="bg-zinc-900/50 border border-zinc-800/50 p-8 rounded-2xl shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] hover:border-zinc-700/50 transition-colors"
            >
              <div className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-br from-white to-zinc-500 mb-4 tracking-tight">
                {stat.value}
              </div>
              <h3 className="text-lg font-semibold text-zinc-100 mb-2">
                {stat.subtitle}
              </h3>
              <p className="text-sm text-zinc-400 leading-relaxed">
                {stat.detail}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
