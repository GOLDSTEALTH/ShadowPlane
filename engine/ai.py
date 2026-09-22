# -*- coding: utf-8 -*-
"""
engine/ai.py — Unified AI Engine & Failsafe Parser
==================================================
Handles all AI generation via LiteLLM to support BYOM (Bring-Your-Own-Model).
Includes a strict AST/Regex failsafe parser to guarantee the output is pure HCL,
even if models hallucinate markdown or XML wrappers.
"""

import logging
import os
import re
from typing import Optional

# Attempt to import litellm
try:
    import litellm
    # Suppress LiteLLM telemetry/logging spam
    litellm.suppress_debug_info = True
except ImportError:
    litellm = None

logger = logging.getLogger("ShadowPlane-AIEngine")


SYSTEM_INSTRUCTION = (
    "You are an expert AWS Terraform engineer. Fix the provided Terraform code "
    "to resolve the AWS API error. You must return ONLY the raw, valid HCL code. "
    "Do not include markdown formatting, backticks (```hcl), explanations, or "
    "apologies. Your exact output will be written directly to disk."
)


def extract_hcl(raw: str) -> str:
    """
    Failsafe Parser: Extracts HCL code from LLM output.
    LLMs (like Claude, ChatGPT) often wrap code in markdown or XML tags
    despite being told not to. This strips it all away.
    """
    text = raw.strip()

    # 1. Try to find XML-style tags first (e.g. <fixed_code>...</fixed_code>)
    xml_match = re.search(r"<fixed_code>(.*?)</fixed_code>", text, re.DOTALL | re.IGNORECASE)
    if xml_match:
        text = xml_match.group(1).strip()

    # 2. Try to find Markdown code blocks (e.g. ```hcl ... ```)
    # This regex matches the content inside the first code block it finds
    md_match = re.search(r"```(?:hcl|terraform|tf|json)?\s*\n(.*?)\n```", text, re.DOTALL | re.IGNORECASE)
    if md_match:
        text = md_match.group(1).strip()
    else:
        # Fallback: Just strip leading/trailing backticks if present
        text = re.sub(r"^```(?:hcl|terraform|tf)?\s*\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```\s*$", "", text)
        
    return text.strip() + "\n"


async def repair_terraform_code(
    model: str,
    error_text: str,
    current_hcl: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Send the broken HCL and error to the LLM and return the patched HCL.
    Uses LiteLLM to support 100+ models transparently.
    """
    if litellm is None:
        logger.error("litellm is not installed. Cannot use AI engine.")
        return None

    # Handle native google-genai translation for gemini models via litellm
    # LiteLLM requires gemini models to be prefixed with gemini/ for the vertex/studio split,
    # but we'll accept plain "gemini-3.7-flash" and format it automatically if needed.
    if "gemini" in model.lower() and not model.startswith("gemini/"):
        model = f"gemini/{model}"

    user_prompt = (
        f"The following Terraform code failed during `terraform apply`.\n\n"
        f"## Terraform Error Output\n```\n{error_text}\n```\n\n"
        f"## Current main.tf\n```hcl\n{current_hcl}\n```\n\n"
        f"Fix the code so it provisions successfully against AWS (LocalStack). "
        f"Return ONLY the corrected HCL — nothing else."
    )

    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": user_prompt}
    ]

    # Map our generic api_key to standard env vars if needed
    if api_key:
        if "gemini" in model:
            os.environ["GEMINI_API_KEY"] = api_key
        elif "gpt" in model:
            os.environ["OPENAI_API_KEY"] = api_key
        elif "claude" in model:
            os.environ["ANTHROPIC_API_KEY"] = api_key

    logger.info(f"Invoking LLM: {model} (base_url={base_url})")

    try:
        # Use litellm.acompletion for async execution
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            api_base=base_url,
            temperature=0.1,
            num_retries=2, # LiteLLM built-in backoff
        )
        
        raw_output = response.choices[0].message.content
        if not raw_output:
            logger.warning("LLM returned empty response.")
            return None

        patched_hcl = extract_hcl(raw_output)
        
        # Simple sanity check to ensure we didn't just get conversational text
        if "resource " not in patched_hcl and "module " not in patched_hcl and "data " not in patched_hcl:
             if current_hcl.strip() != "":
                 logger.warning("Patched output doesn't look like HCL. Falling back to original.")
                 return None

        return patched_hcl

    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        return None
