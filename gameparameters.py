from dataclasses import dataclass
from typing import Optional
import socket
import ipaddress
import urllib.request

@dataclass
class GameParameters:
    is_host: bool
    is_public_host: bool
    own_local_ip: str
    own_external_ip: Optional[str]
    remote_server_ip: Optional[str]
    player_name: str

    def __post_init__(self):
        self.player_name = self.player_name.strip()

        #validate flags
        if self.is_public_host:
            assert self.is_host

        #validate local ip
        local_address_obj = get_ip_address_object(self.own_local_ip)
        assert local_address_obj.version == 4, "not ipv4"
        assert local_address_obj.is_private, "ip not private"

        #validate external ip
        if self.is_public_host:
            external_address_obj = get_ip_address_object(self.own_external_ip)
            assert external_address_obj.version == 4, "not ipv4"
            assert not external_address_obj.is_private, "ip not external"
            assert not external_address_obj.is_loopback, "ip is localhost"

        # validate remote ip
        if not self.is_host:
            address_obj = get_ip_address_object(self.remote_server_ip)
            assert address_obj.version == 4, "not ipv4"

        #validate name
        assert self.player_name != None and self.player_name != "", "no name"
        assert len(self.player_name) <= 20, "too long name"

    def get_server_ip(self):
        if self.is_host and not self.is_public_host:
            server_ip = self.own_local_ip
        elif self.is_public_host:
            server_ip = self.own_external_ip
        elif not self.is_host:
            server_ip = self.remote_server_ip
        else:
            raise Exception("Unexpected flag combination")

        assert server_ip != None
        assert server_ip != ""
        return server_ip

def get_local_ip():
    ip_list = socket.gethostbyname_ex('')[2]

    for ip in ip_list:
        try:
            address_obj = get_ip_address_object(ip)
            assert address_obj.version == 4, "not ipv4"
            assert address_obj.is_private, "not local"
            assert not address_obj.is_loopback, "localhost"

            print(f"Valid local ip found: {ip}")
            return ip
        except Exception as exception:
            print(f"Invalid local ip {ip}: {exception} ({type(exception).__name__})")

    raise Exception("No valid local ip was found. Please specify it manually.")

def get_external_ip():
    ip = urllib.request.urlopen("https://v4.ident.me/").read().decode('utf8')

    try:
        address_obj = get_ip_address_object(ip)
        assert address_obj.version == 4, "not ipv4"
        assert not address_obj.is_private, "not external"
        assert not address_obj.is_loopback, "localhost"
    except Exception as exception:
        raise Exception(f"Invalid external ip {ip}: {exception}") from exception

    print(f"Valid external ip found: {ip}")
    return ip

def get_ip_address_object(ip_string: Optional[str]):
    try:
        assert ip_string != None
        return ipaddress.IPv4Address(ip_string)
    except Exception as ex:
        raise Exception(f"Failed to interpret ip address '{ip_string}'") from ex
