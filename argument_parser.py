import argparse
from dataclasses import dataclass

@dataclass
class ParsedArguments:
    client_only: bool
    connect_directly: bool


def get_arguments():
    parser = argparse.ArgumentParser(description = "A simple multiplayer shooting game.")
    parser.add_argument('--client_only', action="store_true",
        help="don't start a new server, connect to an existing one")
    parser.add_argument("--connect_directly", action="store_true",
        help="this client and created server shall communicate without internet")

    arguments = parser.parse_args()
    arguments = ParsedArguments(
        client_only = arguments.client_only,
        connect_directly = arguments.connect_directly
    )

    if arguments.client_only and arguments.connect_directly:
        raise Exception("Invalid argument combination (client_only & connect_directly).\n"
            + "Connection to a remote server requiers internet.")

    return arguments
