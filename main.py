import os
import shutil

from dotenv import load_dotenv
from lcpcli import Lcpcli

from download import Nakala
from convert import Convert

load_dotenv()

COLLECTION_ID = "10.34847%2Fnkl.ebcdd191"
DOWNLOAD_DIR = os.path.join(".", "download")
CORPUS_DIR = os.path.join(".", "corpus")

API_KEY = os.environ.get("API_KEY", "")
API_SECRET = os.environ.get("API_SECRET", "")
PROJECT = os.environ.get("PROJECT", "")


def run():

    nak = Nakala(COLLECTION_ID)
    nak.download_all(where=DOWNLOAD_DIR)

    cvt = Convert(DOWNLOAD_DIR)
    cvt.convert(output=CORPUS_DIR)

    # copy wav files
    media_dir = os.path.join(CORPUS_DIR, "media")
    if os.path.exists(media_dir):
        shutil.rmtree(media_dir)
    if not os.path.exists(media_dir):
        os.makedirs(media_dir)
    for f in os.listdir(DOWNLOAD_DIR):
        if not f.endswith(".wav"):
            continue
        shutil.copy(os.path.join(DOWNLOAD_DIR, f), os.path.join(media_dir, f))

    Lcpcli(
        corpus=CORPUS_DIR,
        api_key=API_KEY,
        secret=API_SECRET,
        project=PROJECT,
        live=True,
        check_only=False,
    )


if __name__ == "__main__":
    run()
