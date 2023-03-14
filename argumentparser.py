import argparse
from gameparameters import GameParameters, get_local_ip

def get_arguments():
    parser = argparse.ArgumentParser(
        description = "A simple multiplayer shooting game. If any arguments are specified, you will go straight into the game.")
    parser.add_argument("client_type", choices=["host", "guest"],
        help="host = start a server, guest = join a server")
    parser.add_argument("name",
        help="Your name")
    parser.add_argument("-s", "--server_ip", default=None,
        help="Ip address of the server (only specify for guest).")
    parser.add_argument("-l", "--local_ip", default=None,
        help="Local ip address (ipv4) of this machine. The game should be able to find this automatically.")
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
    
    if arguments.local_ip == None:
        arguments.local_ip = get_local_ip()
    
    arguments = GameParameters(
        is_host = is_host,
        local_ip = arguments.local_ip,
        remote_server_ip = arguments.server_ip,
        player_name = arguments.name
    )

    return arguments
