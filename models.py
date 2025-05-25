import datetime
from dataclasses import dataclass

from loguru import logger


@dataclass
class Message:
    id: int
    time_stamp: int
    sender_qq: str
    interlocutor_qq: str
    types: str
    raw_content: dict
    direction: int

    @property
    def time(self):
        return datetime.datetime.fromtimestamp(self.time_stamp)

    @property
    def content(self):
        return self.raw_content

    def parse_section(self, section: dict):
        msg_body = ""
        section_type = section.get("type", None)
        section_content = section.get("content", None)

        if section_type is None or section_type == "None":
            msg_body += section_content if section_content is not None else ""
        elif section_type == "[文本]":
            msg_body += section_content
        elif section_type == "[图片]":
            msg_body += "[图片]"
        elif "[被引用的消息]" in section_type:
            msg_body += "<quote>"

            msg_body += self.parse_section(
                {
                    "type": section_type.replace("[被引用的消息]", ""),
                    "content": section_content,
                }
            )
            msg_body += "</quote>"
        elif section_type == "":
            return ""
        elif section_type == "[应用消息]" or section_type == "[提示]":
            return ""
        else:
            msg_body += section_type + " " + section_content
            if msg_body == "None None":
                logger.info(f"2 None msg: {self.content}")

        return msg_body

    def __expr__(self):
        msg_body = ""
        for section in self.content:
            if section.get("content") == "[自动回复]":
                break
            msg_body += self.parse_section(section)
        return msg_body

    def __repr__(self):
        return self.__expr__()

    def __str__(self):
        return self.__expr__()

    def __json__(self):
        return self.__expr__()
