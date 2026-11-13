import os
import httpx

class SlackNotifier:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL", "")

    def _truncate_diff(self, original: str, patched: str, max_lines: int = 30) -> str:
        import difflib
        orig_lines = original.splitlines(keepends=True)
        patch_lines = patched.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            orig_lines, patch_lines,
            fromfile="Original", tofile="Patched",
            lineterm=""
        ))
        
        if not diff:
            return "No differences detected."
        
        if len(diff) > max_lines:
            diff = diff[:max_lines] + [f"\n... ({len(diff) - max_lines} more lines truncated) ..."]
        
        return "".join(diff)

    def send_verification_success(self, pr_number: str, original_hcl: str, patched_hcl: str) -> bool:
        if not self.webhook_url:
            print("[Slack] No SLACK_WEBHOOK_URL configured, skipping notification.")
            return False
            
        diff_text = self._truncate_diff(original_hcl, patched_hcl)
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"✅ ShadowPlane Verification Passed (PR #{pr_number})",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Verification Complete against LocalStack/Checkov.*\n\n*Results (Truncated):*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{diff_text}```"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🔗 Review the full results in the Pull Request. | ShadowPlane Autonomous Verification"
                    }
                ]
            }
        ]
        
        try:
            response = httpx.post(self.webhook_url, json={"blocks": blocks})
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[Slack] Failed to send webhook: {e}")
            return False

    def send_attestation_report(self, pr_number: str, attestation_md: str, success: bool) -> bool:
        """Posts the Markdown attestation summary directly to Slack."""
        if not self.webhook_url:
            print("[Slack] No SLACK_WEBHOOK_URL configured, skipping notification.")
            return False

        header_text = f"✅ ShadowPlane Verification Passed (PR #{pr_number})" if success else f"❌ ShadowPlane Verification Failed (PR #{pr_number})"

        # Slack mrkdwn blocks have a 3000 character limit
        content = attestation_md if len(attestation_md) <= 2900 else attestation_md[:2900] + "\n\n_...(truncated)_"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text,
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": content
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🛡️ ShadowPlane Verification Gateway"
                    }
                ]
            }
        ]

        try:
            response = httpx.post(self.webhook_url, json={"blocks": blocks})
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[Slack] Failed to send webhook: {e}")
            return False
