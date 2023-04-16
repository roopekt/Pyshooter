import argparse
from gameparameters import GameParameters, get_local_ip, get_external_ip

def get_arguments():
    parser = argparse.ArgumentParser(
        description = "A simple multiplayer shooting game. If any arguments are specified, you will go straight into the game.")
    parser.add_argument("client_type", choices=["host.l", "host.p", "guest"],
        help="host.l = start a server on LAN, host.p = start a server on public internet, guest = join a server")
    parser.add_argument("name",
        help="Your name")
    parser.add_argument("-s", "--server_ip", default=None,
        help="Ip address of the server (only specify for guest).")
    parser.add_argument("-l", "--local_ip", default=None,
        help="Local ip address (ipv4) of this machine. The game should be able to find this automatically.")
    parser.add_argument("-e", "--external_ip", default=None,
        help="External ip address (ipv4) of this machine. The game should be able to find this automatically.")
    arguments = parser.parse_args()

    if arguments.client_type == "host.l":
        is_host = True
        is_public_host = False
    elif arguments.client_type == "host.p":
        is_host = True
        is_public_host = True
    elif arguments.client_type == "guest":
        is_host = False
        is_public_host = False
    else:
        raise Exception(f"Unknown client type {arguments.client_type}")
    
    if is_host and arguments.server_ip != None:
        raise Exception("Please don't specify server_ip for host.")
    elif (not is_host) and arguments.server_ip == None:
        raise Exception("Expected a server_ip.")
    
    if arguments.local_ip == None:
        arguments.local_ip = get_local_ip()
    if arguments.external_ip == None and is_public_host:
        arguments.external_ip = get_external_ip()
    
    arguments = GameParameters(
        is_host = is_host,
        is_public_host = is_public_host,
        own_local_ip = arguments.local_ip,
        own_external_ip = arguments.external_ip,
        remote_server_ip = arguments.server_ip,
        player_name = arguments.name
    )

    return arguments
