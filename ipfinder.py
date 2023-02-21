import socket
import ipaddress

def get_local_ip():
    ip_list = socket.gethostbyname_ex('')[2]

    for ip in ip_list:
        try:
            address = ipaddress.IPv4Address(ip)
            assert address.version == 4, "not ipv4"
            assert address.is_private, "not local"
            assert not address.is_loopback, "localhost"

            print(f"Valid local ip found: {address}")
            return ip
        except Exception as exception:
            print(f"Invalid local ip {ip}: {exception} ({type(exception).__name__})")

    raise Exception("No valid local ip was found. Please specify it manually.")
