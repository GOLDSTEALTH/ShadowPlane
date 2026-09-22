"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const faqs = [
  {
    question: "Does ShadowPlane download my production state files?",
    answer: "No. Downloading production terraform.tfstate files exposes secrets (like DB passwords) to the AI. Instead, ShadowPlane uses a 'Two-Stage Pre-Warm' strategy. It clones your main branch into LocalStack to build a mock state, then checks out your PR branch to test the transition. Your real state never leaves your VPC.",
  },
  {
    question: "Whose AWS credentials does it use?",
    answer: "None. ShadowPlane physically intercepts all AWS API calls made by Terraform and routes them to a local emulator (LocalStack). It requires zero real AWS credentials to function.",
  },
  {
    question: "Which AI models are supported?",
    answer: "ShadowPlane is built on LiteLLM, meaning you can Bring-Your-Own-Model (BYOM). We natively support GPT-4o, Claude 3.5 Sonnet, Gemini 3.7, and even local open-source models like Ollama / LLaMA 3.",
  },
  {
    question: "How does it prevent 'hallucinations' from breaking my code?",
    answer: "Our engine uses a strict AST/Regex Failsafe Parser. If a model hallucinates markdown fences, conversational text, or XML wrappers, the parser strips it away and extracts only valid HCL.",
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
