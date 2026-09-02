"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform, useInView } from "framer-motion";

/* ── Node data ─────────────────────────────────────────────────────── */
const nodes = [
  {
    side: "left" as const,
    tag: "SECURITY",
    title: "Zero-Trust Isolation",
    body: "Shared-kernel Docker MVP transitioning to Firecracker microVMs. Strict zero network egress to live AWS environments.",
    visual: (
      <div className="font-mono text-xs leading-6 bg-zinc-950 border border-zinc-800 p-4 mt-4 rounded-lg overflow-x-auto">
        <span className="text-zinc-600">$</span>{" "}
        <span className="text-cyan-400">docker network disconnect</span>{" "}
        <span className="text-zinc-400">bridge</span>{" "}
        <span className="text-emerald-400">shadowplane-sandbox</span>
      </div>
    ),
  },
  {
    side: "right" as const,
    tag: "POLICY",
    title: "Token Guardrails",
    body: "Agent rigidly scoped via FastMCP to parse only .tf files. Physically blocked from scanning state files or massive .terraform directories.",
    visual: (
      <div className="font-mono text-xs leading-7 bg-zinc-950 border border-zinc-800 p-4 mt-4 rounded-lg">
        <div className="text-zinc-500">demo-infra/</div>
        <div className="pl-5">
          <span className="text-zinc-700">├─</span>{" "}
          <span className="text-zinc-600 line-through">.terraform/</span>
          <span className="text-red-500/70 ml-3 text-xs font-semibold">BLOCKED</span>
        </div>
        <div className="pl-5">
          <span className="text-zinc-700">├─</span>{" "}
          <span className="text-zinc-600 line-through">terraform.tfstate</span>
          <span className="text-red-500/70 ml-3 text-xs font-semibold">BLOCKED</span>
        </div>
        <div className="pl-5">
          <span className="text-zinc-700">└─</span>{" "}
          <span className="text-white font-semibold">main.tf</span>
          <span className="text-emerald-500 ml-3 text-xs font-semibold">ALLOWED</span>
        </div>
      </div>
    ),
  },
  {
    side: "left" as const,
    tag: "PERFORMANCE",
    title: "Latency & Fallbacks",
    body: "Sub-100ms cold starts via Warm Pools. Dynamic model degradation (Gemini 3.7 → 3.6) ensures pipeline resiliency during LLM API capacity spikes.",
    visual: (
      <div className="flex flex-wrap items-center gap-3 mt-4">
        <div className="font-mono text-xs bg-zinc-950 border border-zinc-800 px-4 py-2.5 rounded-lg flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-zinc-500">Cold Start:</span>
          <span className="text-emerald-400 font-bold text-sm">84ms</span>
        </div>
        <div className="font-mono text-xs bg-zinc-950 border border-zinc-800 px-4 py-2.5 rounded-lg flex items-center gap-2.5">
          <span className="text-zinc-500">Model:</span>
          <span className="text-cyan-400 font-semibold">3.7</span>
          <span className="text-zinc-600">→</span>
          <span className="text-yellow-400 font-semibold">3.6</span>
        </div>
      </div>
    ),
  },
  {
    side: "right" as const,
    tag: "SAFETY",
    title: "The Escape Hatch",
    body: "Mandatory human review gates for destructive operations (terraform destroy). Direct webhook bypass if the interception gateway experiences downtime.",
    visual: (
      <div className="font-mono text-xs leading-7 bg-zinc-950 border border-zinc-800 p-4 mt-4 rounded-lg overflow-x-auto whitespace-pre">
        <span className="text-zinc-600">{"{"}</span>
        {"\n"}
        <span className="pl-5">
          <span className="text-zinc-500">{'"'}</span>
          <span className="text-cyan-400">require_human_approval</span>
          <span className="text-zinc-500">{'"'}: </span>
          <span className="text-emerald-400 font-semibold">true</span>
          <span className="text-zinc-600">,</span>
        </span>
        {"\n"}
        <span className="pl-5">
          <span className="text-zinc-500">{'"'}</span>
          <span className="text-cyan-400">blocked_operations</span>
          <span className="text-zinc-500">{'"'}: </span>
          <span className="text-yellow-300">[{'"'}destroy{'"'}, {'"'}taint{'"'}]</span>
        </span>
        {"\n"}
        <span className="text-zinc-600">{"}"}</span>
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
        <div className="bg-zinc-900/50 border border-zinc-800 backdrop-blur-md p-7 md:p-8 rounded-xl hover:border-zinc-700 transition-colors">
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
    offset: ["start 80%", "end 20%"],
  });

  const scaleY = useTransform(scrollYProgress, [0, 1], [0, 1]);

  return (
    <div className="max-w-6xl mx-auto px-6">
      {/* Section header */}
      <div className="text-center mb-20">
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
          style={{ scaleY, transformOrigin: "top" }}
          className="
            absolute
            left-[14px] md:left-1/2 md:-translate-x-px
            top-0 bottom-0 w-[2px]
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
