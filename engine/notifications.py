import os
import httpx

class SlackNotifier:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL", "")

    def _truncate_diff(self, original: str, patched: str, max_lines: int = 10) -> str:
        orig_lines = original.splitlines()
        patch_lines = patched.splitlines()
        
        diff_str = "--- Original\n+++ Patched\n"
        for i in range(min(len(orig_lines), max_lines)):
            if i < len(patch_lines) and orig_lines[i] != patch_lines[i]:
                diff_str += f"- {orig_lines[i]}\n+ {patch_lines[i]}\n"
        
        if len(orig_lines) > max_lines or len(patch_lines) > max_lines:
            diff_str += "\n... (diff truncated) ..."
            
        return diff_str or "No visible differences in first 10 lines."

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
                    "text": "*AI Auto-Repair applied and verified against LocalStack/Checkov.*\n\n*HCL Diff (Truncated):*"
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
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve & Merge",
                            "emoji": True
                        },
                        "style": "primary",
                        "value": f"approve_pr_{pr_number}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Reject",
                            "emoji": True
                        },
                        "style": "danger",
                        "value": f"reject_pr_{pr_number}"
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
