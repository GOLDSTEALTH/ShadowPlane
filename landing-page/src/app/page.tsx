import HeroPipeline from "@/components/HeroPipeline";
import DiffViewer from "@/components/DiffViewer";
import EngineeringSpecs from "@/components/EngineeringSpecs";

export default function Home() {
  return (
    <main className="min-h-screen bg-stone-100">
      {/* Top Navigation Bar */}
      <nav className="border-b border-stone-300 px-6 md:px-12 py-3 flex items-center justify-between bg-white">
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold text-stone-900 tracking-tight">
            ◇ SHADOWPLANE
          </span>
          <span className="text-[10px] text-stone-400 tracking-wider border border-stone-300 px-2 py-0.5">
            v0.1.0
          </span>
        </div>
        <div className="flex items-center gap-6">
          <a
            href="https://github.com/GOLDSTEALTH/ShadowPlane"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-stone-600 hover:text-orange-600 transition-colors tracking-wider uppercase"
          >
            GitHub
          </a>
          <a
            href="#specs"
            className="text-xs text-stone-600 hover:text-orange-600 transition-colors tracking-wider uppercase"
          >
            Specs
          </a>
          <span className="text-[10px] font-bold text-white bg-orange-600 px-3 py-1.5 tracking-wider uppercase cursor-pointer hover:bg-orange-700 transition-colors">
            Deploy →
          </span>
        </div>
      </nav>

      {/* Component A: Hero Pipeline Schematic */}
      <HeroPipeline />

      {/* Component B: Audit Trail / Diff Viewer */}
      <DiffViewer />

      {/* Component C: Engineering Specs */}
      <div id="specs">
        <EngineeringSpecs />
      </div>

      {/* Footer */}
      <footer className="px-6 md:px-12 py-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white border-t border-stone-300">
        <div>
          <span className="text-xs text-stone-500">
            ShadowPlane · Autonomous CI/CD Gatekeeper
          </span>
          <span className="text-xs text-stone-400 ml-2">
            © {new Date().getFullYear()} GOLDSTEALTH
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[10px] text-stone-400 tracking-wider">
            BUILT WITH: NEXT.JS · FASTAPI · LOCALSTACK · GEMINI
          </span>
        </div>
      </footer>
    </main>
  );
}
