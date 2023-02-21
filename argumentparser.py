import argparse
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedArguments:
    is_host: bool
    local_ip: str
    remote_server_ip: Optional[str]

def get_arguments():
    parser = argparse.ArgumentParser(
        description = "A simple multiplayer shooting game. With no arguments, a host will be started on localhost.")
    parser.add_argument("client_type", choices=["host", "guest"],
                        help="host = start a server, guest = join a server")
    parser.add_argument("local_ip",
                        help="Local ip address (ipv4) of this machine.")
    parser.add_argument("-s", "--server_ip", default=None,
                        help="Ip address of the server (only specify for guest).")
    arguments = parser.parse_args()

    if arguments.client_type == "host":
        is_host = True
    elif arguments.client_type == "guest":
        is_host = False
    else:
        raise Exception(f"Unknown client type {arguments.client_type}")
    
    if is_host and arguments.server_ip != None:
        raise Exception("Please don't specify server_ip for host.")
    elif (not is_host) and arguments.server_ip == None:
        raise Exception("Expected a server_ip.")
    
    arguments = ParsedArguments(
        is_host = is_host,
        local_ip = arguments.local_ip,
        remote_server_ip = arguments.server_ip
    )

    return arguments
