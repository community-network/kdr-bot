from typing import Optional

from pydantic import BaseModel

from database.dto.users import User


class ServerRef(BaseModel):
    server_id: int
    discord_id: int
    username: str
    kdr_role_id: Optional[float]


class UserServers(BaseModel):
    user_id: int
    player_id: int
    discord_id: int
    servers: list[ServerRef]

    def to_user(self, server: ServerRef) -> User:
        return User(
            user_id=self.user_id,
            player_id=self.player_id,
            server_id=server.server_id,
            discord_id=server.discord_id,
            username=server.username,
            kdr_role_id=server.kdr_role_id,
        )
