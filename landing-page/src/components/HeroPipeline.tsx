export default function HeroPipeline() {
  const nodes = [
    {
      id: "trigger",
      label: "GITHUB PR PUSH",
      sublabel: "feature/iam-fix → main",
      status: "neutral" as const,
      icon: "↗",
    },
    {
      id: "blocked",
      label: "BLOCKED",
      sublabel: "AWS API ValidationException: InvalidBucketName",
      status: "error" as const,
      icon: "✕",
    },
    {
      id: "sandbox",
      label: "SHADOWPLANE SANDBOX",
      sublabel: "LocalStack v4.3 · us-east-1 · Isolated Docker Network",
      status: "neutral" as const,
      icon: "◇",
    },
    {
      id: "heal",
      label: "FASTMCP AUTO-HEAL",
      sublabel: "Gemini 3.7-flash → 3.6-flash fallback · temp=0.1",
      status: "neutral" as const,
      icon: "⚙",
    },
    {
      id: "resolved",
      label: "RESOLVED",
      sublabel: "Blast Radius Contained · sys.exit(0) · Pipeline GREEN",
      status: "success" as const,
      icon: "✓",
    },
  ];

  return (
    <section className="border-b border-stone-300">
      {/* Header */}
      <div className="border-b border-stone-300 px-6 py-8 md:px-12 md:py-12">
        <p className="text-xs tracking-[0.3em] text-stone-500 uppercase mb-3">
          ShadowPlane v0.1.0 · Autonomous CI/CD Gatekeeper
        </p>
        <h1 className="text-3xl md:text-5xl font-bold text-stone-900 leading-tight">
          The Flight Simulator
          <br />
          for Terraform.
        </h1>
        <p className="mt-4 text-sm text-stone-600 max-w-2xl leading-relaxed">
          Intercept AI-generated infrastructure before it reaches production.
          ShadowPlane provisions every Terraform plan inside an isolated
          LocalStack sandbox, self-heals failures with Gemini, and enforces
          strict exit codes to gate your CI/CD pipeline.
        </p>
      </div>

      {/* Pipeline Flowchart */}
      <div className="px-6 py-8 md:px-12">
        <p className="text-[10px] tracking-[0.3em] text-stone-400 uppercase mb-6">
          Execution Trace · Pipeline Schematic
        </p>

        <div className="flex flex-col">
          {nodes.map((node, i) => (
            <div key={node.id}>
              {/* Node */}
              <div
                className={`
                  border p-4 md:p-5 flex items-start gap-4
                  ${
                    node.status === "error"
                      ? "border-red-600 bg-red-50"
                      : node.status === "success"
                      ? "border-green-700 bg-green-50"
                      : "border-stone-300 bg-white"
                  }
                `}
              >
                {/* Step number */}
                <div
                  className={`
                    w-8 h-8 flex items-center justify-center text-xs font-bold shrink-0 border
                    ${
                      node.status === "error"
                        ? "border-red-600 text-red-700 bg-red-100"
                        : node.status === "success"
                        ? "border-green-700 text-green-800 bg-green-100"
                        : "border-stone-400 text-stone-600 bg-stone-50"
                    }
                  `}
                >
                  {node.icon}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <span
                      className={`
                        text-[10px] tracking-[0.2em] font-semibold uppercase
                        ${
                          node.status === "error"
                            ? "text-red-700"
                            : node.status === "success"
                            ? "text-green-800"
                            : "text-stone-500"
                        }
                      `}
                    >
                      STEP {String(i).padStart(2, "0")}
                    </span>
                    <span
                      className={`
                        text-sm md:text-base font-bold
                        ${
                          node.status === "error"
                            ? "text-red-800"
                            : node.status === "success"
                            ? "text-green-900"
                            : "text-stone-900"
                        }
                      `}
                    >
                      {node.label}
                    </span>
                  </div>
                  <p
                    className={`
                      text-xs mt-1
                      ${
                        node.status === "error"
                          ? "text-red-600"
                          : node.status === "success"
                          ? "text-green-700"
                          : "text-stone-500"
                      }
                    `}
                  >
                    {node.sublabel}
                  </p>
                </div>

                {/* Status indicator */}
                <div
                  className={`
                    text-[10px] tracking-wider font-semibold uppercase px-2 py-1 border shrink-0
                    ${
                      node.status === "error"
                        ? "border-red-600 text-red-700 bg-red-100"
                        : node.status === "success"
                        ? "border-green-700 text-green-800 bg-green-100"
                        : "border-stone-300 text-stone-500 bg-stone-50"
                    }
                  `}
                >
                  {node.status === "error"
                    ? "HALT"
                    : node.status === "success"
                    ? "PASS"
                    : "EXEC"}
                </div>
              </div>

              {/* Connector line */}
              {i < nodes.length - 1 && (
                <div className="flex items-center ml-[1.75rem] h-6">
                  <div
                    className={`
                      w-px h-full
                      ${
                        node.status === "error"
                          ? "bg-red-400"
                          : node.status === "success"
                          ? "bg-green-500"
                          : "bg-stone-300"
                      }
                    `}
                  />
                  <span className="text-[9px] text-stone-400 ml-3 tracking-wider">
                    │
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
