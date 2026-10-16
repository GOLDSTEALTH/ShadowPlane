"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const faqs = [
  {
    question: "Does ShadowPlane download my production state files?",
    answer: "No. Downloading production terraform.tfstate files exposes secrets (like DB passwords). Instead, ShadowPlane uses state sanitization to redact sensitive attributes and outputs, and can pre-warm state from your base branch directly into LocalStack. Your production credentials and real secrets never leave your VPC.",
  },
  {
    question: "Whose AWS credentials does it use?",
    answer: "None. ShadowPlane executes Terraform with mock credentials (AWS_ACCESS_KEY_ID=test) and forces all provider API endpoints to LocalStack. It requires zero real cloud credentials to execute verification.",
  },
  {
    question: "How does ShadowPlane contain malicious local-exec provisioners or rogue scripts?",
    answer: "ShadowPlane executes Terraform inside an ephemeral, isolated Docker sandbox container. Host files are mounted safely, host environment variables and AWS credentials are stripped, and network egress is restricted solely to the local emulator, preventing local machine escape.",
  },
  {
    question: "How does Change-Risk Intelligence protect production databases and state?",
    answer: "ShadowPlane parses the Terraform Plan JSON to detect any actions that force the deletion or replacement of stateful resources (such as S3 buckets, RDS clusters, and KMS keys) and detects IAM privilege broadening, flagging critical risks before any apply is attempted.",
  },
  {
    question: "What is the Cryptographic Attestation pack?",
    answer: "Every verification run generates an immutable, tamper-evident SHA-256 evidence hash and markdown attestation card containing the exact Git commit SHA, Checkov security results, and change-risk metrics for GitHub PR comments and CI merge gates.",
  },
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggle = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section className="py-24 bg-zinc-950 border-t border-zinc-800/60">
      <div className="max-w-4xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            Security & Architecture FAQ
          </h2>
          <p className="mt-4 text-zinc-400">
            Engineered from the ground up for zero-trust environments.
          </p>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, idx) => {
            const isOpen = openIndex === idx;
            return (
              <div
                key={idx}
                className="border border-zinc-800 rounded-xl bg-zinc-900/50 overflow-hidden"
              >
                <button
                  onClick={() => toggle(idx)}
                  className="w-full text-left px-6 py-5 flex items-center justify-between focus:outline-none"
                >
                  <span className="font-semibold text-zinc-100">{faq.question}</span>
                  <span
                    className={`text-zinc-500 transition-transform duration-300 ${
                      isOpen ? "rotate-180" : ""
                    }`}
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </span>
                </button>

                <AnimatePresence>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: "easeInOut" }}
                    >
                      <div className="px-6 pb-5 text-zinc-400 leading-relaxed">
                        {faq.answer}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
