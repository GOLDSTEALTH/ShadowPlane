"use client";

import { useState, useEffect, useRef } from "react";

// --- Types ---
type WsStatus = "connecting" | "connected" | "error";
type JobStatus = "idle" | "processing" | "verified" | "failed";
type StepName = "preflight" | "attempt1" | "analysis" | "attempt2" | "success";

interface JobDetails {
  repo: string;
  branch: string;
  pr_number: string | number;
  sender: string;
  status: JobStatus;
  raw_payload?: any;
}

interface LogEntry {
  id: number;
  text: string;
  level: string;
}

interface DiffData {
  original: string;
  patched: string;
}

const STEPS_CONFIG: { id: StepName; label: string }[] = [
  { id: "preflight", label: "Pre-Flight Reset" },
  { id: "attempt1", label: "Attempt 1 (Failing)" },
  { id: "analysis", label: "FastMCP Analysis" },
  { id: "attempt2", label: "Attempt 2 (Patched)" },
  { id: "success", label: "Verification Passed" },
];

export default function WebhooksDashboard() {
  const [wsStatus, setWsStatus] = useState<WsStatus>("connecting");
  const [queueDepth, setQueueDepth] = useState<number>(0);
  const [jobDetails, setJobDetails] = useState<JobDetails | null>(null);
  const [activeStep, setActiveStep] = useState<StepName | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [diffData, setDiffData] = useState<DiffData | null>(null);
  const [payloadOpen, setPayloadOpen] = useState(false);

  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  // WebSocket Logic
  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimer: NodeJS.Timeout;

    const connect = () => {
      setWsStatus("connecting");
      // Use standard browser WS, mock URL for UI dev if not available
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      // Pointing to localhost:8000 where the python fastapi web_server.py is running
      const wsUrl = `${protocol}://${window.location.hostname}:8000/ws`;

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsStatus("connected");
      };

      ws.onclose = () => {
        setWsStatus("error");
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        setWsStatus("error");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          switch (data.type) {
            case "job":
              setJobDetails({
                repo: data.repo || "—",
                branch: data.branch || "—",
                pr_number: data.pr_number || "—",
                sender: data.sender || "—",
                status: "processing",
                raw_payload: data.raw_payload || data,
              });
              setLogs([
                {
                  id: Date.now(),
                  text: `[WEBHOOK] New job: PR #${data.pr_number} on ${data.repo}@${data.branch} by ${data.sender}`,
                  level: "info",
                },
              ]);
              setDiffData(null);
              setActiveStep("preflight");
              break;

            case "queue":
              setQueueDepth(data.depth || 0);
              break;

            case "log":
              setLogs((prev) => [
                ...prev,
                { id: Date.now() + Math.random(), text: data.content, level: data.level || "info" },
              ]);
              break;

            case "step":
              setActiveStep(data.step as StepName);
              break;

            case "diff":
              setDiffData({ original: data.original, patched: data.patched });
              break;

            case "done":
              setActiveStep("success");
              setJobDetails((prev) => (prev ? { ...prev, status: "verified" } : null));
              setLogs((prev) => [
                ...prev,
                { id: Date.now(), text: "\n[OK] ShadowPlane Verification Passed.", level: "success" },
              ]);
              break;

            case "error":
              setJobDetails((prev) => (prev ? { ...prev, status: "failed" } : null));
              setLogs((prev) => [
                ...prev,
                { id: Date.now(), text: "\n[FAIL] Verification Failed.", level: "error" },
              ]);
              break;
          }
        } catch (err) {
          console.error("Failed to parse WS message", err);
        }
      };
    };

    connect();

    return () => {
      if (ws) ws.close();
      clearTimeout(reconnectTimer);
    };
  }, []);

  // Helpers
  const getStepStatus = (stepId: StepName): "pending" | "active" | "completed" => {
    if (!activeStep) return "pending";
    const currentIndex = STEPS_CONFIG.findIndex((s) => s.id === activeStep);
    const stepIndex = STEPS_CONFIG.findIndex((s) => s.id === stepId);
    if (stepIndex < currentIndex) return "completed";
    if (stepIndex === currentIndex) return "active";
    return "pending";
  };

  const getLogColor = (level: string) => {
    switch (level) {
      case "error": return "text-red-500";
      case "warn": return "text-yellow-500";
      case "success": return "text-emerald-500";
      default: return "text-zinc-300";
    }
  };

  return (
    <div className="min-h-screen bg-black text-zinc-100 p-4 sm:p-6 md:p-10 font-sans overflow-x-hidden">
      <header className="mb-6 sm:mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
        <h1 className="text-xl sm:text-2xl font-semibold tracking-tight">Webhook Interception</h1>
        <div className="flex items-center gap-2.5 bg-zinc-950 border border-zinc-800 px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg shrink-0">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              wsStatus === "connected"
                ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"
                : wsStatus === "connecting"
                ? "bg-yellow-500 animate-pulse"
                : "bg-red-500"
            }`}
          />
          <span className="text-xs sm:text-sm text-zinc-400 capitalize font-medium">{wsStatus}</span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* ── LEFT COLUMN ─────────────────────────────────────────────── */}
        <div className="lg:col-span-4 flex flex-col gap-8">
          
          {/* Configuration Block */}
          <section className="bg-zinc-950 border border-zinc-800 rounded-lg p-6">
            <h2 className="text-sm font-semibold text-zinc-100 mb-4 uppercase tracking-wider">
              Endpoint Configuration
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Payload URL</label>
                <input
                  type="text"
                  readOnly
                  value="https://api.deenlabs.tech/v1/webhook"
                  className="w-full bg-black border border-zinc-800 text-zinc-300 font-mono text-xs px-3 py-2 rounded-md focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Signing Secret</label>
                <input
                  type="password"
                  readOnly
                  value="whsec_1234567890abcdef"
                  className="w-full bg-black border border-zinc-800 text-zinc-300 font-mono text-xs px-3 py-2 rounded-md focus:outline-none"
                />
              </div>
            </div>
          </section>

          {/* Webhook Monitor */}
          <section className="bg-zinc-950 border border-zinc-800 rounded-lg p-6 flex-1">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-semibold text-zinc-100 uppercase tracking-wider">
                Monitor
              </h2>
              <div className="text-xs font-mono bg-black border border-zinc-800 px-2 py-1 rounded">
                QUEUE: <span className="text-cyan-400 font-bold">{queueDepth}</span>
              </div>
            </div>

            {!jobDetails ? (
              <div className="text-center py-10 border border-dashed border-zinc-800 rounded-lg bg-black/50">
                <span className="text-zinc-600 text-sm">Listening for GitHub Events...</span>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Repository</span>
                    <span className="font-mono text-zinc-200 truncate block">{jobDetails.repo}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Branch</span>
                    <span className="font-mono text-cyan-400 truncate block">{jobDetails.branch}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Pull Request</span>
                    <span className="font-mono text-zinc-200">#{jobDetails.pr_number}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Status</span>
                    <span
                      className={`font-mono text-xs uppercase tracking-wider font-bold ${
                        jobDetails.status === "processing" ? "text-yellow-500" :
                        jobDetails.status === "verified" ? "text-emerald-500" :
                        jobDetails.status === "failed" ? "text-red-500" : "text-zinc-500"
                      }`}
                    >
                      {jobDetails.status}
                    </span>
                  </div>
                </div>

                {/* Collapsible Payload */}
                <div className="border border-zinc-800 rounded-md overflow-hidden bg-black">
                  <button
                    onClick={() => setPayloadOpen(!payloadOpen)}
                    className="w-full px-4 py-2 text-xs font-mono text-zinc-400 hover:text-zinc-200 bg-zinc-950 flex items-center justify-between border-b border-zinc-800 transition-colors"
                  >
                    <span>raw_payload.json</span>
                    <span>{payloadOpen ? "−" : "+"}</span>
                  </button>
                  {payloadOpen && (
                    <pre className="p-4 text-[10px] leading-5 font-mono text-zinc-500 overflow-x-auto max-h-48 overflow-y-auto">
                      {JSON.stringify(jobDetails.raw_payload, null, 2)}
                    </pre>
                  )}
                </div>

                {/* Timeline */}
                <div className="pt-4">
                  <h3 className="text-[10px] text-zinc-500 uppercase tracking-widest mb-4">Execution Timeline</h3>
                  <div className="flex flex-col gap-3 relative before:absolute before:inset-0 before:ml-2.5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-zinc-800">
                    {STEPS_CONFIG.map((step, idx) => {
                      const status = getStepStatus(step.id);
                      return (
                        <div key={step.id} className="relative flex items-center gap-4">
                          <div
                            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 z-10 bg-black ${
                              status === "completed" ? "border-emerald-500 text-emerald-500" :
                              status === "active" ? "border-cyan-500 text-cyan-500" :
                              "border-zinc-800 text-transparent"
                            }`}
                          >
                            {status === "completed" && (
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                            {status === "active" && <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-ping" />}
                          </div>
                          <span
                            className={`text-sm font-medium ${
                              status === "completed" ? "text-emerald-500" :
                              status === "active" ? "text-cyan-400" :
                              "text-zinc-600"
                            }`}
                          >
                            {step.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

              </div>
            )}
          </section>
        </div>

        {/* ── RIGHT COLUMN ────────────────────────────────────────────── */}
        <div className="lg:col-span-8 flex flex-col gap-8">
          
          {/* Terminal Window */}
          <section className="bg-zinc-950 border border-zinc-800 rounded-lg flex flex-col overflow-hidden h-[400px]">
            {/* Title Bar */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-black">
              <span className="w-3 h-3 rounded-full bg-red-500/80" />
              <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <span className="w-3 h-3 rounded-full bg-green-500/80" />
              <span className="text-xs text-zinc-500 font-mono ml-3">ShadowPlane Intercept Logs</span>
            </div>
            
            {/* Logs Body */}
            <div className="flex-1 p-4 bg-black overflow-y-auto font-mono text-xs leading-relaxed whitespace-pre-wrap">
              {logs.map((log) => (
                <div key={log.id} className={`${getLogColor(log.level)}`}>
                  {log.text}
                </div>
              ))}
              <div ref={terminalEndRef} />
            </div>
          </section>

          {/* Diff Viewer */}
          <section className="bg-zinc-950 border border-zinc-800 rounded-lg flex flex-col overflow-hidden h-[400px]">
             {/* Title Bar */}
             <div className="flex items-center gap-4 px-4 py-3 border-b border-zinc-800 bg-black">
              <span className="text-xs font-semibold text-zinc-100 uppercase tracking-widest">
                Infrastructure Auto-Repair
              </span>
              {diffData && (
                <span className="text-[10px] text-cyan-500 border border-cyan-900 bg-cyan-950/30 px-2 py-0.5 rounded font-mono">
                  SHADOWPATCH APPLIED
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto bg-black p-4 font-mono text-xs leading-6">
              {!diffData ? (
                <div className="h-full flex flex-col items-center justify-center text-zinc-600 border border-dashed border-zinc-800 rounded-md">
                  <svg className="w-8 h-8 mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  <span>No patches applied yet.</span>
                  <span>Wait for a failure analysis.</span>
                </div>
              ) : (
                <div className="flex flex-col gap-4">
                  {/* Original */}
                  <div className="border border-red-900/50 rounded-md overflow-hidden">
                    <div className="bg-red-950/30 px-3 py-1 border-b border-red-900/50 text-red-500 text-[10px] uppercase font-bold tracking-wider">
                      Removed (- Original)
                    </div>
                    <pre className="p-3 text-red-300 bg-red-950/10 overflow-x-auto">
                      {diffData.original}
                    </pre>
                  </div>
                  {/* Patched */}
                  <div className="border border-emerald-900/50 rounded-md overflow-hidden">
                    <div className="bg-emerald-950/30 px-3 py-1 border-b border-emerald-900/50 text-emerald-500 text-[10px] uppercase font-bold tracking-wider">
                      Added (+ Patched)
                    </div>
                    <pre className="p-3 text-emerald-300 bg-emerald-950/10 overflow-x-auto">
                      {diffData.patched}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
