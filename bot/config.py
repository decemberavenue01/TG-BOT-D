from dataclasses import dataclass
from dotenv import load_dotenv
import os
from typing import List

load_dotenv()

@dataclass
class Config:
    bot_token: str
    admins: List[int]
    auto_approve: bool

def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN не задан в .env")

    admins_str = os.getenv("ADMINS", "")
    admins = [int(x) for x in admins_str.split(",") if x.strip().isdigit()]

    auto_approve = os.getenv("AUTO_APPROVE", "false").lower() == "true"

    return Config(
        bot_token=bot_token,
        admins=admins,
        auto_approve=auto_approve
    )
