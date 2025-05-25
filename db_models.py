from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    create_engine,
    JSON,
    TIMESTAMP,
)
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime
from loguru import logger

from models import Message

ModelBase = declarative_base()


class DBMessage(ModelBase):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    time_stamp = Column(Integer)
    sender_qq = Column(String)
    interlocutor_qq = Column(String)
    types = Column(String)
    raw_content = Column("contents", JSON)
    direction = Column(Integer)

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


def types_map_fun(x: DBMessage):
    x.types = str(x.types).split("|")
    return x


def load_db_messages(filepath: str):
    alchemy_engine = create_engine(f"sqlite:///{filepath}")
    Session = sessionmaker(bind=alchemy_engine)
    session = Session()
    messages = session.query(DBMessage).all()
    messages.sort(key=lambda x: x.time_stamp)
    messages = list(map(types_map_fun, messages))

    logger.success("Loaded {} messages".format(len(messages)))
    all_types = set()
    for i in messages:
        all_types = all_types.union(set(i.types))

    real_messages = []
    for message in messages:
        msg = Message(
            id=message.id,
            time_stamp=message.time_stamp,
            sender_qq=message.sender_qq,
            interlocutor_qq=message.interlocutor_qq,
            types=message.types,
            raw_content=message.content,
            direction=message.direction,
        )
        real_messages.append(msg)

    logger.debug("All types: {}".format(all_types))

    # return messages
    return real_messages
