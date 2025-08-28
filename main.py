import json
import os
import shutil
import sys

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

AUDIO_FORMAT = "mp3"


def touch(fname):
    try:
        os.utime(fname, None)
    except OSError:
        open(fname, "a").close()


def run(
    apikey: str = API_KEY,
    apisecret: str = API_SECRET,
    project: str = PROJECT,
    test: bool = False,
    dummy_audio: bool = False,
    upload: bool = True,
    convert: bool = True,
    download: bool = True,
):

    if download:
        nak = Nakala(COLLECTION_ID)
        nak.download_all(where=DOWNLOAD_DIR, do_audio=not dummy_audio)

    if convert:
        cvt = Convert(DOWNLOAD_DIR)
        cvt.convert(output=CORPUS_DIR, audio_format=AUDIO_FORMAT)

    # copy wav files
    media_dir = os.path.join(CORPUS_DIR, "media")
    if os.path.exists(media_dir):
        shutil.rmtree(media_dir)
    if not os.path.exists(media_dir):
        os.makedirs(media_dir)

    if dummy_audio:
        with open(
            os.path.join(CORPUS_DIR, "interview.csv"), "r", encoding="utf-8"
        ) as itv:
            while line := itv.readline():
                media = line.split(",")[2].strip()
                if not media.startswith('"{""audio"": ""'):
                    continue
                audiofile = media[15:-4]
                touch(os.path.join(media_dir, audiofile))

    else:
        if AUDIO_FORMAT:
            import ffmpeg

            print(f"Converting the audio files to {AUDIO_FORMAT}")
        else:
            print("Copying the audio files to the corpus folder...")
        for f in os.listdir(DOWNLOAD_DIR):
            if not f.endswith(".wav"):
                continue
            dest_fn = f[:-4] + f".{AUDIO_FORMAT}" if AUDIO_FORMAT else f
            source = os.path.join(DOWNLOAD_DIR, f)
            dest = os.path.join(media_dir, dest_fn)
            if os.path.exists(dest):
                print(f"Found an existing file at {dest} -- skipping")
            if AUDIO_FORMAT:
                ffmpeg.input(source).output(dest).run()
            else:
                shutil.copy(source, dest)
        print("All the audio files were placed to the corpus folder!")

    if not upload:
        print("Not uploading, done!")
        return

    if test:
        print(
            "Warning: you are uploading to your local instance of LCP, not to production."
        )
    Lcpcli(
        corpus=CORPUS_DIR,
        api_key=apikey,
        secret=apisecret,
        project=project,
        live=not test,
        check_only=False,
    )


if __name__ == "__main__":
    kwargs: dict = {}
    if "test" in sys.argv:
        kwargs["test"] = True
    if "dummy" in sys.argv:
        kwargs["dummy_audio"] = True
    if apikey := next((x for x in sys.argv if x.startswith("apikey=")), None):
        kwargs["apikey"] = apikey[7:]
    if apisecret := next((x for x in sys.argv if x.startswith("apisecret=")), None):
        kwargs["apisecret"] = apisecret[10:]
    if project := next((x for x in sys.argv if x.startswith("project=")), None):
        kwargs["project"] = project[8:]
    if upload := next((x for x in sys.argv if x.startswith("upload=")), None):
        kwargs["upload"] = upload[7:].lower() not in ("0", "false", "no")
    if convert := next((x for x in sys.argv if x.startswith("convert=")), None):
        kwargs["convert"] = convert[8:].lower() not in ("0", "false", "no")
    if download := next((x for x in sys.argv if x.startswith("download=")), None):
        kwargs["download"] = download[9:].lower() not in ("0", "false", "no")
    run(**kwargs)
