from dataclasses import dataclass
from configobj import ConfigObj
import validate


@dataclass
class DiscordBot:
    discord_bot_token: str
    db_url: str
    server_id: int
    kdr_roles: dict[float, int]

    @staticmethod
    def from_conf(config: ConfigObj):
        db_url = config["db_url"]
        discord_bot_token = config["discord_bot_token"]
        server_id = config.as_int("server_id")
        kdr_roles = {}
        for min_kdr, role_id in config["kd_roles"].items():  # type: ignore
            kdr_roles[float(min_kdr)] = int(role_id)
        return DiscordBot(
            discord_bot_token=discord_bot_token,  # type: ignore
            db_url=db_url,  # type: ignore
            server_id=server_id,
            kdr_roles=kdr_roles,
        )


@dataclass
class Config:
    bot: DiscordBot


def load_config() -> Config:
    path = "settings.ini"
    config = ConfigObj(path, configspec="config_spec.ini")
    validator = validate.Validator()
    valid = config.validate(validator, copy=True)
    if not valid:
        print("settings.ini is missing settings!")
    config.filename = path
    config.write()

    return Config(
        bot=DiscordBot.from_conf(config),
    )
