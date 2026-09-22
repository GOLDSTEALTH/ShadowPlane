import os
import subprocess
import shutil
import logging

logger = logging.getLogger("ShadowPlane-Git")

def clone_and_checkout(repo_url: str, base_branch: str, head_branch: str, dest_dir: str) -> bool:
    """
    Clones the repository and checks out the base branch, preparing it for a two-stage deploy.
    Returns True if successful, False otherwise.
    """
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
            ["git", "checkout", base_branch],
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
    logger.info(f"Switching to branch: {branch_name}")
    try:
        subprocess.run(
            ["git", "checkout", branch_name],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git checkout {branch_name} failed: {e.stderr}")
        return False
