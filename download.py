import hashlib
import os
import requests

NAKALA_API = "https://api.nakala.fr/"
PER_PAGE = 50
NPAGE = "{npage}"


class Nakala:
    def __init__(self, collection_id: str):
        self.collection_id = collection_id

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

    def download_all(self, where: str = "output"):
        if not os.path.exists(where):
            os.makedirs(where)
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
            if skip_wav:
                print(f"Found {pwav} with same sha1 -- skipping")
            else:
                print(f"Downloading {wav['name']}...")
                rwav = requests.get(dl_template.format(did=did, sha=wav["sha1"]))
                with open(pwav, "wb") as owav:
                    owav.write(rwav.content)
                print(f"Download of {wav['name']} complete at {pwav}")
            if n > 9:
                break
            n += 1
        print(f"Found {n} files")
