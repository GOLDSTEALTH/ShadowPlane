"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform, useInView } from "framer-motion";

/* ── Node data ─────────────────────────────────────────────────────── */
const nodes = [
  {
    side: "left" as const,
    tag: "EMULATION",
    title: "State-Aware Emulation",
    body: "Executes dry-runs against an anonymized, sanitized replica of your production terraform.tfstate, avoiding blank-slate false positives.",
    visual: (
      <div className="font-mono text-xs leading-6 bg-zinc-950 border border-zinc-800 p-4 mt-4 rounded-lg overflow-x-auto whitespace-pre">
        <span className="text-zinc-600">$</span>{" "}
        <span className="text-cyan-400">terraform state pull</span>{" "}
        <span className="text-zinc-500">|</span>{" "}
        <span className="text-emerald-400">shadowplane sanitize</span>{" "}
        <span className="text-zinc-500">{">"}</span>{" "}
        <span className="text-zinc-300">mock.tfstate</span>
      </div>
    ),
  },
  {
    side: "right" as const,
    tag: "GUARDRAILS",
    title: "Shift-Left Security Guardrails",
    body: "Pipes ShadowPatch-generated patches through Checkov/tfsec. Instantly rejects and re-prompts the AI if the proposed fix violates security compliance.",
    visual: (
      <div className="font-mono text-xs leading-6 bg-zinc-950 border border-zinc-800 p-4 mt-4 rounded-lg overflow-x-auto">
        <div className="text-red-400 font-semibold mb-1">
          [checkov] FAILED: CKV_AWS_20
        </div>
        <div className="text-zinc-500 mb-2 ml-4 border-l-2 border-red-500/30 pl-3">
          S3 bucket has an ACL defined which allows public access.
        </div>
        <div className="text-cyan-400 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          [shadowplane] Re-Routing to ShadowPatch for compliance fix...
        </div>
      </div>
    ),
  },
  {
    side: "left" as const,
    tag: "AUTO-HEAL",
    title: "Full-Stack Auto-Healing",
    body: "Goes beyond bare metal. Dynamically generates inventory and auto-heals failed Ansible playbook tasks inside simulated compute nodes.",
    visual: (
      <div className="font-mono text-[11px] leading-5 bg-zinc-950 border border-zinc-800 p-4 mt-4 rounded-lg overflow-x-auto whitespace-pre">
        <span className="text-zinc-600">{"{"}</span>
        {"\n"}
        <span className="pl-4">
          <span className="text-zinc-500">{'"'}task{'"'}: </span>
          <span className="text-zinc-300">{'"'}Install Nginx{'"'}</span><span className="text-zinc-600">,</span>
        </span>
        {"\n"}
        <span className="pl-4">
          <span className="text-zinc-500">{'"'}status{'"'}: </span>
          <span className="text-red-400 font-bold">{'"'}failed{'"'}</span><span className="text-zinc-600">,</span>
        </span>
        {"\n"}
        <span className="pl-4">
          <span className="text-zinc-500">{'"'}msg{'"'}: </span>
          <span className="text-yellow-300">{'"'}No package matching 'nginxxx' found{'"'}</span>
        </span>
        {"\n"}
        <span className="text-zinc-600">{"}"}</span>
      </div>
    ),
  },
  {
    side: "right" as const,
    tag: "CHATOPS",
    title: "Interactive ChatOps",
    body: "Mandatory human-in-the-loop oversight. Pushes side-by-side diffs and compliance reports directly to Slack for 1-click approvals.",
    visual: (
      <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950 p-4 font-sans flex flex-col gap-3">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-4 h-4 bg-zinc-800 rounded flex items-center justify-center text-[8px]">Slack</div>
          <span className="text-xs font-semibold text-zinc-300">ShadowPlane Bot</span>
          <span className="text-[10px] text-zinc-600">12:34 PM</span>
        </div>
        <p className="text-xs text-zinc-400 border-l-2 border-emerald-500 pl-3">
          ✅ AI Auto-Repair verified against LocalStack & Checkov.
        </p>
        <div className="flex gap-3 mt-1">
          <button className="px-3 py-1.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold hover:bg-emerald-500/20 transition-colors">
            Approve & Merge
          </button>
          <button className="px-3 py-1.5 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold hover:bg-red-500/20 transition-colors">
            Reject
          </button>
        </div>
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
