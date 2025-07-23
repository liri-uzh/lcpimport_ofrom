import aiohttp
import asyncio
import hashlib
import os
import requests

NAKALA_API = "https://api.nakala.fr/"
PER_PAGE = 50
NPAGE = "{npage}"
CONCURRENT_DOWNLOADS = 4


class Nakala:
    def __init__(self, collection_id: str):
        self.collection_id = collection_id

    @classmethod
    async def download_audio(self, session, sem, wav, dl_template, did, pwav):
        print(f"Downloading {wav['name']}...")
        url = dl_template.format(did=did, sha=wav["sha1"])
        try:
            async with sem, session.get(url=url) as response:
                rwav = await response.read()
                with open(pwav, "wb") as owav:
                    owav.write(rwav)
            print(f"Download of {wav['name']} complete at {pwav}")
        except Exception as e:
            print("Unable to get url {} due to {}.".format(url, e.__class__))

    @classmethod
    async def download_audios(self, all_audios: list):
        print("Downloading the audios")
        sem = asyncio.Semaphore(CONCURRENT_DOWNLOADS)
        async with aiohttp.ClientSession() as session:
            ret = await asyncio.gather(
                *(Nakala.download_audio(session, sem, *params) for params in all_audios)
            )
        print("Finished downloading the audios")

    def list_files(self):
        url_template = f"{NAKALA_API}collections/{self.collection_id}/datas?page={NPAGE}&limit={PER_PAGE}"
        npage = 1
        while r := requests.get(
            url_template.format(npage=npage), headers={"accept": "application/json"}
        ):
            rjson = r.json()
            for d in rjson["data"]:
                yield (d["identifier"], d["files"])
            npage += 1
            if rjson["currentPage"] == rjson["lastPage"]:
                break

    def download_all(self, where: str = "output", do_audio: bool = True):
        if not os.path.exists(where):
            os.makedirs(where)

        all_audios = []

        dl_template = NAKALA_API + "data/{did}/{sha}?content-disposition=attachment"
        n = 0
        for id, files in self.list_files():
            tei = next((f for f in files if f.get("name", "").endswith(".tei")), None)
            wav = next((f for f in files if f.get("name", "").endswith(".wav")), None)
            if tei is None or wav is None:
                continue
            did = id.replace("/", "%2F")
            ptei = os.path.join(where, tei["name"])
            skip_tei = (
                os.path.exists(ptei)
                and hashlib.sha1(open(ptei, "rb").read()).hexdigest() == tei["sha1"]
            )
            if skip_tei:
                print(f"Found {ptei} with same sha1 -- skipping")
            else:
                print(f"Downloading {tei['name']}...")
                rtei = requests.get(dl_template.format(did=did, sha=tei["sha1"]))
                with open(ptei, "wb") as otei:
                    otei.write(rtei.content)
                print(f"Download of {tei['name']} complete at {ptei}")
            pwav = os.path.join(where, wav["name"])
            skip_wav = (
                os.path.exists(pwav)
                and hashlib.sha1(open(pwav, "rb").read()).hexdigest() == wav["sha1"]
            )
            if not do_audio:
                print("Asked to skip audio, so skipping audio")
            elif skip_wav:
                print(f"Found {pwav} with same sha1 -- skipping")
            else:
                all_audios.append((wav, dl_template, did, pwav))
                print(f"Scheduled a download for {wav['name']}")
            n += 1
        print(f"Found {n} files")

        if all_audios:
            asyncio.run(Nakala.download_audios(all_audios))
