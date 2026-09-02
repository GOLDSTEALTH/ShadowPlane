import Navbar from "@/components/Navbar";
import TerminalDiff from "@/components/TerminalDiff";
import ScrollPipeline from "@/components/ScrollPipeline";
import IntegrationMatrix from "@/components/IntegrationMatrix";
import BusinessROI from "@/components/BusinessROI";
import Quickstart from "@/components/Quickstart";

export default function Home() {
  return (
    <main className="min-h-screen bg-zinc-950">
      {/* ── Nav ─────────────────────────────────────────────────────── */}
      <Navbar />

      {/* ── Hero ────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Subtle radial glow */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[300px] sm:w-[600px] h-[300px] sm:h-[600px] bg-cyan-500/5 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 pt-12 sm:pt-20 md:pt-24 pb-12 sm:pb-16 text-center">
          <div className="text-4xl xs:text-5xl sm:text-7xl md:text-8xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-zinc-500 tracking-tight sm:tracking-tighter mb-4 sm:mb-6 break-words max-w-full">
            ShadowPlane
          </div>
          <p className="text-xs sm:text-sm text-cyan-500 font-medium tracking-wide mb-4 sm:mb-6 uppercase">
            Autonomous CI/CD Gatekeeper
          </p>
          <h1 className="text-2xl xs:text-3xl sm:text-5xl md:text-7xl font-bold text-white leading-[1.15] tracking-tight">
            The Flight Simulator
            <br className="hidden xs:inline" />{" "}
            for Terraform.
          </h1>
          <p className="mt-4 sm:mt-6 text-base sm:text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto leading-relaxed">
            Intercept broken Terraform configurations, sandbox them in LocalStack, and auto-heal AWS API failures via the autonomous ShadowPatch engine.
          </p>

          {/* CTAs */}
          <div className="mt-8 sm:mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 w-full max-w-xs sm:max-w-none mx-auto">
            <a
              href="https://github.com/GOLDSTEALTH/ShadowPlane"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white text-zinc-900 px-6 py-3 rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors"
            >
              <svg
                className="w-4 h-4"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
              View GitHub
            </a>
            <a
              href="#specs"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 border border-zinc-700 text-zinc-300 px-6 py-3 rounded-lg text-sm font-semibold hover:border-zinc-500 hover:text-white transition-colors"
            >
              Read the Architecture
              <span className="text-zinc-500">→</span>
            </a>
          </div>
        </div>
      </section>

      {/* ── Interactive Demo ─────────────────────────────────────────── */}
      <section id="demo" className="px-6 pb-24">
        <TerminalDiff />
      </section>

      {/* ── Divider with label ───────────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-6">
        <div className="border-t border-zinc-800" />
      </div>

      {/* ── Engineering Specs ────────────────────────────────────────── */}
      <section id="specs" className="pt-24">
        <ScrollPipeline />
      </section>

      {/* ── Integration Matrix ───────────────────────────────────────── */}
      <IntegrationMatrix />

      {/* ── Business ROI ─────────────────────────────────────────────── */}
      <BusinessROI />

      {/* ── Quickstart ───────────────────────────────────────────────── */}
      <Quickstart />

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-zinc-800/60 py-8">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-sm text-zinc-500">
            ShadowPlane · © {new Date().getFullYear()} GOLDSTEALTH
          </span>
          <span className="text-xs text-zinc-600 font-mono">
            Next.js · FastAPI · LocalStack · ShadowPatch
          </span>
        </div>
      </footer>
    </main>
  );
}
