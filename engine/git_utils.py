import os
import re
import subprocess
import shutil
import logging

logger = logging.getLogger("ShadowPlane-Git")

def _is_safe_ref(ref: str) -> bool:
    """Validate that a git branch or commit reference does not contain command injection characters."""
    if not ref or not isinstance(ref, str):
        return False
    return bool(re.match(r"^[a-zA-Z0-9._/-]+$", ref)) and not ref.startswith("-")

def clone_and_checkout(repo_url: str, base_branch: str, head_branch: str, dest_dir: str) -> bool:
    """
    Clones the repository and checks out the base branch, preparing it for a two-stage deploy.
    Returns True if successful, False otherwise.
    """
    if not _is_safe_ref(base_branch):
        logger.error("Unsafe base branch reference: %s", base_branch)
        return False
    if head_branch and not _is_safe_ref(head_branch):
        logger.error("Unsafe head branch reference: %s", head_branch)
        return False

    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
        
    os.makedirs(dest_dir, exist_ok=True)
    
    # 1. Clone the repository
    logger.info(f"Cloning {repo_url} into {dest_dir}...")
    try:
        subprocess.run(
            ["git", "clone", repo_url, "."],
            cwd=dest_dir,
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Git clone failed: {e.stderr}")
        return False
        
    # 2. Checkout base branch
    logger.info(f"Checking out base branch: {base_branch}")
    try:
        subprocess.run(
            ["git", "checkout", "--", base_branch],
            cwd=dest_dir,
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Git checkout {base_branch} failed: {e.stderr}")
        return False
        
    return True

def checkout_branch(repo_dir: str, branch_name: str) -> bool:
    """
    Switches an existing repository to the target branch.
    """
    if not _is_safe_ref(branch_name):
        logger.error("Unsafe branch reference: %s", branch_name)
        return False

    logger.info(f"Switching to branch: {branch_name}")
    try:
        subprocess.run(
            ["git", "checkout", "--", branch_name],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git checkout {branch_name} failed: {e.stderr}")
        return False
