import datetime

import tqdm
from loguru import logger

from db_models import DBMessage
from models import Message

# __stat_infos = {}
# # __next_msg_special_token = "＜｜nextmsg｜＞"
# __next_msg_special_token = "\n"


def post_process(conversations: list[list[dict]]):
    # 后处理
    for idx in range(len(conversations)):
        cur_dialog = conversations[idx]
        if cur_dialog[0].get("from") == "gpt":
            try:
                assert idx - 1 >= 0  # 避免跑到最后去了
                prev = conversations[idx - 1]
                prev_idx = -1
                while prev[prev_idx].get("from") != "human":
                    prev_idx -= 1
                    cur_dialog[0]["value"] = (
                        prev[prev_idx]["value"] + cur_dialog[0]["value"]
                    )
                # 这个必是human
                cur_dialog.insert(0, prev[prev_idx])
            except AssertionError:
                logger.info("find first human msg not exist")
                cur_dialog.insert(0, {"from": "human", "value": "hi"})

        if cur_dialog[-1].get("from") == "human":
            try:
                next = conversations[idx + 1]
                next_idx = 0
                while next[next_idx].get("from") != "gpt":
                    next_idx += 1
                    cur_dialog[-1]["value"] += next[next_idx]["value"]
                # 这个必是gpt
                cur_dialog.append(next[next_idx])
            except IndexError:
                cur_dialog.append({"from": "gpt", "value": "bye"})
    return conversations


def construct_sharegpt(
    messages: list[list[Message]],
    _next_msg_special_token: str = "\n",
    text_only: bool = False,
) -> list[list[dict]]:
    dialogues = messages
    conversations = []

    for dialog in tqdm.tqdm(dialogues, desc="构造sharegpr数据集"):
        conversation = []
        cur_idx = 0
        cur_role = dialog[0].sender_qq
        cur_direction = 0 if cur_role == dialog[0].interlocutor_qq else 1

        while cur_idx < len(dialog):
            msg = ""
            while cur_idx < len(dialog) and dialog[cur_idx].sender_qq == cur_role:
                if text_only and "[图片]" == str(dialog[cur_idx]):
                    cur_idx += 1
                    continue
                msg = (
                    msg + str(dialog[cur_idx])
                    if msg == ""
                    else msg + _next_msg_special_token + str(dialog[cur_idx])
                )
                cur_idx += 1

            conversation.append(
                {
                    "from": "gpt" if cur_direction == 0 else "human",
                    "value": msg,
                }
            )

            if cur_idx >= len(dialog):
                break

            cur_role = dialog[cur_idx].sender_qq
            cur_direction = 0 if cur_role == dialog[cur_idx].interlocutor_qq else 1

        conversations.append(conversation)

    conversations = post_process(conversations)
    avg_msg_per_conversation, avg_text_per_conversation, max_text_per_conversation = (
        get_average_length(conversations)
    )
    logger.info(f"Average message per conversation: {avg_msg_per_conversation}")
    logger.info(f"Average text per conversation: {avg_text_per_conversation}")
    logger.info(f"Max text per conversation: {max_text_per_conversation}")

    return conversations


def get_average_length(dialogues: list[list[dict]]):
    average_speech = sum(len(dialog) for dialog in dialogues) / len(dialogues)
    average_text_per_conversation = 0

    max_text_per_conversation = 0

    for dialog in dialogues:
        total_text = 0
        for message in dialog:
            total_text += len(message["value"])
        max_text_per_conversation = max(max_text_per_conversation, total_text)
        average_text_per_conversation += total_text / len(dialogues)

    return average_speech, average_text_per_conversation, max_text_per_conversation


class BaseStrategy:
    def __init__(
        self,
    ):

        self._stat_infos = {}

    def divide(self) -> list[list[Message]]:
        raise NotImplementedError


class DayDivideStrategy(BaseStrategy):
    def divide(self, messages: list[Message]):
        earliest_time = datetime.datetime.fromtimestamp(messages[0].time_stamp)
        current_time = earliest_time.replace(hour=4, minute=0, second=0)
        last_time = current_time

        current_msg_idx = 0

        all_chatlogs = []
        chatlog = []

        self._stat_infos["max_single_day_msgs"] = 0
        self._stat_infos["max_msgs_day_time"] = ""

        with tqdm.tqdm(total=len(messages), desc="处理消息列表") as pbar:
            while current_msg_idx < len(messages):
                current_time = current_time + datetime.timedelta(days=1)
                stat__today_msgs = 0
                while (
                    current_msg_idx < len(messages)
                    and messages[current_msg_idx].time_stamp < current_time.timestamp()
                ):

                    pbar.update(1)
                    chatlog.append(messages[current_msg_idx])
                    current_msg_idx += 1
                    stat__today_msgs += 1

                if len(chatlog) > 50:
                    all_chatlogs.append(chatlog.copy())
                    chatlog.clear()

                if stat__today_msgs > self._stat_infos["max_single_day_msgs"]:
                    self._stat_infos["max_single_day_msgs"] = stat__today_msgs
                    self._stat_infos["max_msgs_day_time"] = (
                        current_time - datetime.timedelta(days=1)
                    )
        # logger.debug(all_chatlogs[0])
        # print(all_chatlogs[0])
        if len(chatlog) > 0:
            all_chatlogs.append(chatlog)

        all_chatlogs = [[msg for msg in dialog if str(msg)] for dialog in all_chatlogs]

        overlaped_chatlogs = []
        with tqdm.tqdm(total=len(all_chatlogs), desc="优化消息列表") as pbar:
            for idx in range(0, len(all_chatlogs)):
                pbar.update(1)
                cur_chatlog = all_chatlogs[idx]
                if idx > 0:
                    cur_chatlog = all_chatlogs[idx - 1][-20:-10] + cur_chatlog
                if idx < len(all_chatlogs) - 1:
                    nxt_overlap_len = min(10, len(all_chatlogs[idx + 1]))
                    cur_chatlog = cur_chatlog + all_chatlogs[idx + 1][:nxt_overlap_len]

                overlaped_chatlogs.append(cur_chatlog)

        # filter empty msgs

        overlaped_chatlogs = [
            [msg for msg in dialog if str(msg)] for dialog in overlaped_chatlogs
        ]
        return overlaped_chatlogs


class HourDivideStrategy(BaseStrategy):
    def __init__(self, hours: int | float):
        super().__init__()
        self.hour_interval = hours

    def divide(self, messages: list[Message]):
        earliest_time = datetime.datetime.fromtimestamp(messages[0].time_stamp)
        current_time = earliest_time
        last_time = current_time

        current_msg_idx = 0

        all_chatlogs = []
        chatlog = []

        with tqdm.tqdm(total=len(messages), desc="处理消息列表") as pbar:
            while current_msg_idx < len(messages):
                current_time = datetime.datetime.fromtimestamp(
                    messages[current_msg_idx].time_stamp
                )
                while (
                    current_msg_idx < len(messages)
                    and messages[current_msg_idx].time_stamp - current_time.timestamp()
                    <= 60 * 60 * self.hour_interval
                ):
                    pbar.update(1)
                    chatlog.append(messages[current_msg_idx])
                    current_msg_idx += 1

                if len(chatlog) > 50:
                    all_chatlogs.append(chatlog.copy())
                    chatlog.clear()

        if len(chatlog) > 0:
            all_chatlogs.append(chatlog)

        all_chatlogs = [[msg for msg in dialog if str(msg)] for dialog in all_chatlogs]

        overlaped_chatlogs = []
        with tqdm.tqdm(total=len(all_chatlogs), desc="优化消息列表") as pbar:
            for idx in range(0, len(all_chatlogs)):
                pbar.update(1)
                cur_chatlog = all_chatlogs[idx]
                if idx > 0:
                    cur_chatlog = all_chatlogs[idx - 1][-10:-5] + cur_chatlog
                if idx < len(all_chatlogs) - 1:
                    nxt_overlap_len = min(5, len(all_chatlogs[idx + 1]))
                    cur_chatlog = cur_chatlog + all_chatlogs[idx + 1][:nxt_overlap_len]

                overlaped_chatlogs.append(cur_chatlog)

        # filter empty msgs
        overlaped_chatlogs = [
            [msg for msg in dialog if str(msg)] for dialog in overlaped_chatlogs
        ]
        average_len = sum(len(dialog) for dialog in overlaped_chatlogs) / len(
            overlaped_chatlogs
        )
        logger.info(f"cutted messages average len: {average_len}")
        return overlaped_chatlogs
