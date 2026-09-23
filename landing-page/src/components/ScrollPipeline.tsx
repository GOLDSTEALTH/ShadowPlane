"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform, useInView } from "framer-motion";

/* ── Node data ─────────────────────────────────────────────────────── */
const nodes = [
  {
    side: "right" as const,
    tag: "SECURITY",
    title: "Fail-Closed Scanning",
    body: "Enforces strict Checkov static analysis before any plan executes. Missing scanner binaries block the pipeline to prevent bypasses.",
    visual: (
      <div className="font-mono text-[11px] leading-5 bg-zinc-950 border border-zinc-800 p-4 mt-4 rounded-lg overflow-x-auto whitespace-pre">
        <div className="text-zinc-600 mb-2">
          $ <span className="text-cyan-400">checkov -f main.tf</span>
        </div>
        <div className="text-emerald-400 flex items-center gap-2">
          <span>✓ Passed checks: 14</span>
        </div>
        <div className="text-red-400 flex items-center gap-2">
          <span>✗ Failed checks: 0</span>
        </div>
      </div>
    ),
  },
  {
    side: "left" as const,
    tag: "INTELLIGENCE",
    title: "Change-Risk Analysis",
    body: "Parses 'terraform plan -json' to proactively flag destructive stateful resource drops (RDS/S3) and IAM permission broadening.",
    visual: (
      <div className="font-mono text-[11px] leading-5 bg-zinc-950 border border-zinc-800 p-4 mt-4 rounded-lg overflow-x-auto whitespace-pre">
        <div className="text-red-400 font-semibold mb-1">
          [CRITICAL] High-Risk Deletion Detected
        </div>
        <div className="text-zinc-500 mb-2 border-l-2 border-red-500/30 pl-3">
          aws_db_instance.primary is marked for destroy.
        </div>
        <div className="text-cyan-400 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
          Execution Blocked. Human verification required.
        </div>
      </div>
    ),
  },
  {
    side: "right" as const,
    tag: "ISOLATION",
    title: "LocalStack Execution",
    body: "If the plan is safe, it is physically isolated and applied within an ephemeral LocalStack Docker container to prevent live AWS mutation.",
    visual: (
      <div className="font-mono text-xs leading-6 bg-zinc-950 border border-zinc-800 p-4 mt-4 rounded-lg overflow-x-auto whitespace-pre">
        <span className="text-zinc-600">$</span>{" "}
        <span className="text-cyan-400">terraform apply</span>{" "}
        <span className="text-zinc-500">-var="</span><span className="text-emerald-400">env=sandbox</span><span className="text-zinc-500">"</span>
        <br />
        <span className="text-zinc-400 text-[10px]">
          [sandbox] apply complete! Resources: 3 added, 0 changed.
        </span>
      </div>
    ),
  },
  {
    side: "left" as const,
    tag: "CIRCUIT BREAKER",
    title: "Runaway AI Prevention",
    body: "A robust circuit breaker trips after 4 consecutive failures, physically blocking AI agents from entering infinite retry loops.",
    visual: (
      <div className="font-mono text-xs leading-6 bg-zinc-950 border border-zinc-800 p-4 mt-4 rounded-lg overflow-x-auto whitespace-pre text-zinc-300">
        {"{"}
        {"\n  "}<span className="text-zinc-500">"breaker_status"</span>: <span className="text-red-400">"TRIPPED"</span>,
        {"\n  "}<span className="text-zinc-500">"failure_count"</span>: <span className="text-cyan-400">4</span>,
        {"\n  "}<span className="text-zinc-500">"system_override"</span>: <span className="text-cyan-400">true</span>
        {"\n"}{"}"}
      </div>
    ),
  },
];

/* ── Single timeline node ──────────────────────────────────────────── */
function TimelineNode({
  node,
  index,
}: {
  node: (typeof nodes)[number];
  index: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-60px" });

  const isLeft = node.side === "left";

  return (
    <div
      ref={ref}
      className={`
        relative flex w-full
        md:items-start
        ${isLeft ? "md:justify-start" : "md:justify-end"}
      `}
    >
      {/* ── Dot on the spine ─── */}
      <div
        className={`
          absolute z-10
          left-[7px] md:left-1/2 md:-translate-x-1/2
          top-4
        `}
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={isInView ? { scale: 1 } : { scale: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 20, delay: 0.1 }}
          className="w-4 h-4 rounded-full border-2 border-cyan-500 bg-zinc-950 shadow-[0_0_10px_rgba(6,182,212,0.4)]"
        />
      </div>

      {/* ── Card ─── */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 40 }}
        transition={{ duration: 0.5, ease: "easeOut", delay: 0.15 }}
        className={`
          relative w-full
          pl-10 md:pl-0
          md:w-[calc(50%-2.5rem)]
          ${isLeft ? "md:pr-0" : "md:pl-0"}
        `}
      >
        <div className="bg-zinc-900/50 border border-zinc-800 backdrop-blur-md p-7 md:p-8 rounded-xl hover:border-zinc-700 transition-colors shadow-xl shadow-black/20">
          {/* Tag + index */}
          <div className="flex items-center justify-between mb-4">
            <span className="text-[11px] tracking-widest text-cyan-500 font-mono font-semibold">
              {node.tag}
            </span>
            <span className="text-[11px] text-zinc-600 font-mono">
              NODE-{String(index + 1).padStart(2, "0")}
            </span>
          </div>

          {/* Title */}
          <h3 className="text-lg md:text-xl font-bold text-zinc-100 mb-3">
            {node.title}
          </h3>

          {/* Body */}
          <p className="text-sm md:text-base text-zinc-400 leading-relaxed">
            {node.body}
          </p>

          {/* Technical visual */}
          {node.visual}
        </div>
      </motion.div>
    </div>
  );
}

/* ── Main ScrollPipeline ───────────────────────────────────────────── */
export default function ScrollPipeline() {
  const containerRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 90%", "end 50%"],
  });

  const height = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  return (
    <div className="max-w-6xl mx-auto px-6">
      {/* Section header */}
      <div className="text-center mb-20">
        <p className="text-sm text-cyan-500 font-medium tracking-wide mb-3 uppercase">
          Enterprise Architecture
        </p>
        <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
          Intelligent Policy Engine
        </h2>
        <p className="mt-3 text-zinc-400 max-w-xl mx-auto">
          An autonomous verification layer that sits between your pull requests and your production environments.
        </p>
      </div>

      {/* Timeline container */}
      <div ref={containerRef} className="relative pb-8">
        {/* ── The Spine ─── */}
        {/* Background track */}
        <div
          className="
            absolute
            left-[14px] md:left-1/2 md:-translate-x-px
            top-0 bottom-0 w-[2px]
            bg-zinc-800
          "
        />
        {/* Glowing progress fill */}
        <motion.div
          style={{ height }}
          className="
            absolute
            left-[14px] md:left-1/2 md:-translate-x-px
            top-0 w-[2px]
            bg-cyan-500 shadow-[0_0_12px_rgba(6,182,212,0.5)]
          "
        />

        {/* ── Nodes ─── */}
        <div className="flex flex-col gap-20 md:gap-28 relative">
          {nodes.map((node, i) => (
            <TimelineNode key={node.tag} node={node} index={i} />
          ))}
        </div>

        {/* Terminal dot at the end of the spine */}
        <div className="absolute left-[7px] md:left-1/2 md:-translate-x-1/2 -bottom-2">
          <div className="w-4 h-4 rounded-full bg-cyan-500 shadow-[0_0_12px_rgba(6,182,212,0.5)]" />
        </div>
      </div>
    </div>
  );
}
