import json
import os
import shutil
import xml.etree.ElementTree as ET

from lxml import etree
from lcpcli.builder import Corpus


def replace_first_line(path: str, to_replace: str = "", replace_content: str = ""):
    with open(path, "r+") as f:
        l = f.readline()
        newL = l.replace(to_replace, replace_content).rstrip()
        f.seek(0)
        f.write(newL)


class Convert:
    def __init__(self, input: str):
        self.input = input
        self.c = Corpus(
            "OFROM",
            document="Interview",
            segment="Utterance",
            description="Le corpus Oral de Français de Suisse Romande. Université de Neuchâtel",
        )
        self.agents = {}
        self.time_offset = 0

    def get_frame(self, ms: str | int):
        ms = int(ms)
        return self.time_offset + round(25.0 * ms / 1000.0)

    def process_document(self, filename: str):

        filepath = os.path.join(self.input, filename)

        # First replace utf encoding
        replace_first_line(filepath, "utf_8", "utf-8")

        with open(filepath, "r") as input:

            parser = etree.XMLParser(recover=True, encoding="utf-8")
            tree = ET.parse(input, parser=parser)  # type: ignore
            # m = re.match(r"\{.*\}", tree.getroot().tag)
            # namespace = m.group(0) if m else ""
            namespace = "{http://www.w3.org/XML/1998/namespace}"

            audio = tree.find(".//{*}media").get("url")
            if not os.path.exists(os.path.join(self.input, audio)):
                print(f"WARNING: could not find audio file {audio} in {self.input}")

            name = tree.find(".//{*}title/{*}desc").text

            for person in tree.findall(".//{*}listPerson/{*}person"):
                person_id = person.find(".//{*}altGrp/{*}alt").get("type")
                if person_id in self.agents:
                    continue
                self.agents[person_id] = self.c.Agent(
                    {
                        x.get("type"): x.text
                        for x in person.findall(".//{*}noteGrp/{*}note")
                    }
                )

            times = {
                "#" + x.get(f"{namespace}id"): self.get_frame(x.get("interval") or 0)
                for x in tree.findall(".//{*}timeline/{*}when")
            }

            itv = self.c.Interview(filename=filename, audio=audio, name=name)
            end_itv = times[
                tree.find(".//{*}body/{*}div/{*}head/{*}note[@type='end']").text
            ]
            itv.set_time(
                self.time_offset,
                max(end_itv, self.time_offset + 1),
            )
            itv.set_media("audio", audio)

            for block in tree.findall(".//{*}body/{*}div/{*}annotationBlock"):
                original_text = block.find(".//{*}u/{*}seg").text

                if original_text == "_":
                    continue

                person_id = str(block.get("who"))
                xmlid = block.get(f"{namespace}id")
                ana = block.get("ana")
                utterance = itv.Utterance(
                    text=original_text,
                    xmlid=xmlid,
                    agent=self.agents[person_id],
                    ana=ana,
                )
                utt_start, utt_end = (
                    times[block.get("start")],
                    times[block.get("end")],
                )
                utterance.set_time(utt_start, max(utt_end, utt_start + 1))

                formSpan = block.findall(
                    ".//{*}spanGrp[@type='" + person_id + "[tok_min]']/{*}span"
                )
                posSpan = block.findall(
                    ".//{*}spanGrp[@type='" + person_id + "[pos_min]']/{*}span"
                )
                lemmaSpan = block.findall(
                    ".//{*}spanGrp[@type='" + person_id + "[lemma]']/{*}span"
                )
                mwuSpan = block.findall(
                    ".//{*}spanGrp[@type='" + person_id + "[tok_mwu]']/{*}span"
                )
                mwuPosSpan = block.findall(
                    ".//{*}spanGrp[@type='" + person_id + "[pos_mwu]']/{*}span"
                )

                tokens = {}
                for n, form in enumerate(formSpan):
                    pos = posSpan[n].text  # .split(":")[0]
                    lemma, agreement, conjunction, filler, key, *_ = lemmaSpan[
                        n
                    ].text.split("|")
                    misc = {}
                    if agreement:
                        misc["agreement"] = agreement
                    if filler:
                        misc["filler"] = filler
                    if key:
                        misc["key"] = key
                    if conjunction:
                        misc["conjunction"] = conjunction
                    t = utterance.Token(form.text, pos=pos, lemma=lemma, misc=misc)
                    t_from, t_to = (times[form.get("from")], times[form.get("to")])
                    t.set_time(t_from, max(t_to, t_from + 1))
                    tokens[form.get("from") + form.get("to")] = t
                for n, mwu in enumerate(mwuSpan):
                    mwuFrom = mwu.get("from", "")
                    mwuTo = mwu.get("to", "")
                    mwuFromTo = mwuFrom + mwuTo
                    if mwuFromTo in tokens:
                        continue
                    mwu_tokens = []
                    for token_id, token in tokens.items():
                        tokenFrom, tokenTo = [int(x) for x in token_id.split("#T")[1:]]
                        if tokenTo > int(mwuTo.lstrip("#T")):
                            break
                        if tokenFrom < int(mwuFrom.lstrip("#T")):
                            continue
                        mwu_tokens.append(token)
                    mwuForm = mwu.text
                    mwuPos = mwuPosSpan[n].text  # .split(":")[0]
                    if mwu_tokens:
                        utterance.Mwu(*mwu_tokens, form=mwuForm, pos=mwuPos)
                utterance.make()

            itv.make()

            self.time_offset = itv.get_time()[1] + 1

        # Restore utf encoding for future sha1 comparison purposes
        replace_first_line(filepath, "utf-8", "utf_8")

    def convert(self, output: str = "."):

        if os.path.exists(output):
            shutil.rmtree(output)
        os.makedirs(output)

        for f in os.listdir(self.input):
            if not f.endswith(".tei"):
                continue
            self.process_document(f)

        self.c.make(output)

        # Update some fields in the config
        config_path = os.path.join(output, "config.json")
        config = json.loads(open(config_path, "r").read())
        config["meta"][
            "sample_query"
        ] = """# Find all the utterrances...
Utterance u
    # ... by a speaker from Berne
    agent.region = "Berne"
    # ... that last at least 1s
    end(u) > start(u) + 1

# Look for sequences of tokens in that utterrance...
sequence@u seq
    # ... that contain a token whose pos is 'CON' or 'PRO'
    Token
        pos = /CON|PRO/
    # ... followed by a token whose form is "euh"
    Token
        form = "euh"

# Display the sequences within their segment
results => plain
    context
        u
    entities
        seq"""
        config["tracks"] = {
            "layers": {"Utterance": {"split": ["agent"]}},
            "group_by": ["agent"],
        }

        with open(config_path, "w") as config_output:
            config_output.write(json.dumps(config, indent=4))
