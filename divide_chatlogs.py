import orjson
from loguru import logger

from db_models import load_db_messages
from json_models import load_json_chatlogs
from divide_strategies import (
    BaseStrategy,
    HourDivideStrategy,
    construct_sharegpt,
    DayDivideStrategy,
)
from models import Message
import argparse

__stat_infos = {}
# __next_msg_special_token = "＜｜nextmsg｜＞"
__next_msg_special_token = "\n"

message_loader_map = {
    "json": load_json_chatlogs,
    "db": load_db_messages,
}
divide_strategy_map = {
    "hour": HourDivideStrategy,
    "day": DayDivideStrategy,
}

parser = argparse.ArgumentParser()


def divide_chatlogs(
    messages: list[Message], strategy: BaseStrategy
) -> list[list[Message]]:
    cutted_msgs = strategy.divide(messages)
    logger.success("Cutted messages into {} dialogs".format(len(cutted_msgs)))
    return cutted_msgs


def export_sharegpt(
    dialogues: list[list[Message]],
    text_only: bool = False,
    filename: str = "sharegpt.json",
):
    conversations = construct_sharegpt(dialogues, __next_msg_special_token, text_only)

    logger.success("Exported {} dialogs".format(len(conversations)))
    # logger.debug(structured_dataset[0])
    final_dataset = []

    for dialog in conversations:
        final_dataset.append({"conversations": dialog})
    final_dataset = orjson.dumps(final_dataset, option=orjson.OPT_INDENT_2)
    with open(filename, "wb") as fp:
        fp.write(final_dataset)
    logger.success(f"Exported to {filename}")
    return conversations


def dbgs(flag: int, **kwargs):
    if flag == 1:
        # 展示导出消息前10条
        for i in range(10):
            # idx = rnd.randint(0, len(messages) - 1)
            idx = i
            msg = kwargs.get("message")[idx]
            logger.debug((msg.time, msg.sender_qq, msg))
    elif flag == 2:
        # 写文件debug
        with open("./debug_overlap.json", "wb+") as fp:
            fp.write(
                orjson.dumps(
                    kwargs["cutted_msgs"],
                    option=orjson.OPT_INDENT_2,
                    default=lambda x: str(x),
                )
            )
    elif flag == 3:
        # 统计信息
        logger.debug(
            f"Max singleDay msgs: {__stat_infos['max_single_day_msgs']} at {__stat_infos["max_msgs_day_time"]}"
        )
    elif flag == 4:
        # 简易展示
        for i, dialog in enumerate(kwargs["cutted_msgs"]):
            if i % 100 == 0:
                print("-" * 20)
                print(i, ":", len(dialog))
                print(dialog[0].time, "~", dialog[-1].time, end="")
                print(dialog[0])


def main():
    parser.add_argument("filepath", type=str)
    parser.add_argument(
        "--strategy", "-st", type=str, default="hour", choices=["hour", "day"]
    )
    parser.add_argument("--hour", default=2.0, type=float)
    parser.add_argument("--output", "-o", type=str, default="sharegpt.json")

    args = parser.parse_args()
    time_space = args.hour if args.strategy == "hour" else None
    filetype = args.filepath.split(".")[-1]

    if args.strategy == "hour":
        divider = HourDivideStrategy(hours=time_space)
    elif args.strategy == "day":
        divider = DayDivideStrategy()
    else:
        raise ValueError("Invalid strategy")

    try:
        messages = message_loader_map[filetype](args.filepath)
    except KeyError:
        raise ValueError("Invalid filetype")

    cutted_msgs = divide_chatlogs(messages, divider)
    export_sharegpt(cutted_msgs, filename=args.output)


# # messages = load_db_messages()
# messages = load_json_chatlogs("./2248094142.json")
# cutted_msgs = divide_chatlogs(messages, HourDivideStrategy(hours=0.5))
# export_sharegpt(cutted_msgs, filename="json_divide.json")
if __name__ == "__main__":
    main()
