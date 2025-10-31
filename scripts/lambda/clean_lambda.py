import zipfile
import os
import shutil
import tempfile
import logging

ZIP_PATH = "dist/lambda.zip"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Folders to prune (only safe unused folders)
BOTOCORE_SAFE_PRUNE = [
    "botocore/data/s3/tests",
    "botocore/data/glacier/tests",
]

BOTO3_SAFE_PRUNE = [
    "boto3/examples"
]

def main():
    if not os.path.exists(ZIP_PATH):
        logger.warning("ZIP file %s does not exist. Skipping cleanup.", ZIP_PATH)
        return

    tmp_dir = tempfile.mkdtemp(prefix="lambda_clean_")
    logger.info("Unzipping %s...", ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(tmp_dir)

    # Remove only safe folders
    for folder_list in [BOTOCORE_SAFE_PRUNE, BOTO3_SAFE_PRUNE]:
        for rel in folder_list:
            target = os.path.join(tmp_dir, rel)
            if os.path.exists(target):
                logger.info("Removing %s", target)
                shutil.rmtree(target)

    # Re-create the cleaned zip
    logger.info("Re-zipping cleaned Lambda package...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(tmp_dir):
            for f in files:
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, tmp_dir)
                z.write(abs_path, rel_path)

    shutil.rmtree(tmp_dir)
    logger.info("Cleaned Lambda saved at %s", ZIP_PATH)

if __name__ == "__main__":
    logger.info("Running clean_lambda.py...")
    main()
