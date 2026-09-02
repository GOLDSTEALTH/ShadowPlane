"use client";

import { useState } from "react";

export default function Quickstart() {
  const [copied, setCopied] = useState(false);
  const code = `git clone https://github.com/shadowplane/shadowplane.git\ncd shadowplane && docker-compose up -d`;

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="py-16 sm:py-24 border-t border-zinc-800/60 bg-zinc-950">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
        <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-zinc-100 tracking-tight mb-6 sm:mb-8">
          Deploy the interception proxy locally in 60 seconds.
        </h2>

        {/* Terminal UI */}
        <div className="relative text-left rounded-xl border border-zinc-800 bg-zinc-900 shadow-2xl shadow-black/50 overflow-hidden mx-auto max-w-2xl">
          {/* macOS Title Bar */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-900/80">
            <span className="w-3 h-3 rounded-full bg-red-500/80" />
            <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
            <span className="w-3 h-3 rounded-full bg-green-500/80" />
            <span className="text-xs text-zinc-500 font-mono ml-3 select-none">
              bash — shadowplane
            </span>
          </div>

          {/* Code Body */}
          <div className="relative p-4 sm:p-6 font-mono text-xs sm:text-sm leading-relaxed text-zinc-300 overflow-x-auto whitespace-pre-wrap sm:whitespace-pre break-all sm:break-normal">
            {/* Copy Button */}
            <button
              onClick={handleCopy}
              className="absolute top-4 right-4 p-2 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-100 transition-colors focus:outline-none"
              title="Copy to clipboard"
            >
              {copied ? (
                <svg
                  className="w-4 h-4 text-emerald-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              ) : (
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              )}
            </button>

            <span className="text-cyan-400">git clone</span>{" "}
            https://github.com/shadowplane/shadowplane.git
            <br />
            <span className="text-cyan-400">cd</span> shadowplane{" "}
            <span className="text-zinc-500">&&</span>{" "}
            <span className="text-emerald-400">docker-compose</span> up -d
          </div>
        </div>
      </div>
    </section>
  );
}
