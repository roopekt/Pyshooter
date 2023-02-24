from dataclasses import dataclass
from typing import Optional

@dataclass
class GameParameters:
    is_host: bool
    local_ip: str
    remote_server_ip: Optional[str]
    player_name: str
