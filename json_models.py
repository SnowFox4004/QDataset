import json
from models import Message
import datetime
import os


def extract_types_and_content(message: dict):
    types = set()
    contents = []
    for section in message["contents"]:
        types.add(section[0])
        contents.append({"type": section[0], "content": section[1]})

    return types, contents


def load_json_chatlogs(filepath: str):

    all_msgs = json.load(open(filepath, "r", encoding="utf-8"))
    interlocutor_qq = os.path.basename(filepath).split(".")[0]
    real_msgs = []

    for idx, message in enumerate(all_msgs):
        msg = Message(
            idx,
            int(datetime.datetime.fromisoformat(message["time"]).timestamp()),
            interlocutor_qq if message["direction"] == "收" else 1000000000,
            interlocutor_qq,
            *extract_types_and_content(message),
            1 if message["direction"] == "收" else 0
        )
        real_msgs.append(msg)

    return real_msgs
