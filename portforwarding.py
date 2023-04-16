import upnpy
from  upnpy.ssdp.SSDPDevice import SSDPDevice
from  upnpy.ssdp.SSDPRequest import SSDPRequest
import time
import socket

# Some devices fail to parse, so we need to modify this function to tolerate faulty devices (ignore them)
def tolerant_send_request(self, message):
    self.socket.sendto(message.encode(), (self.SSDP_MCAST_ADDR, self.SSDP_PORT))

    devices = []
    while True:
        try:
            response, addr = self.socket.recvfrom(65507)# UDP packet data limit is 65507 imposed by IPv4
            device = SSDPDevice(addr, response.decode())
            devices.append(device)
            print(f"UPnP: Successfully parsed device: {device}")
        except Exception as ex:
            print(f"UPnP: Failed to parse device. {type(ex).__name__}: {ex}")

            if isinstance(ex, socket.timeout):
                break

    return devices
SSDPRequest._send_request = tolerant_send_request

MAPPING_RULE_DURATION_SECONDS = 10
RULE_UPDATE_DELAY_SECONDS = 5

def flatten_list(l: list):
    return [item for sublist in l for item in sublist]

class PortForwarder:

    def __init__(self, internal_ip: str, internal_port: int, external_ip: str, external_port: int):
        self.internal_ip = internal_ip
        self.internal_port = internal_port
        self.external_ip = external_ip
        self.external_port = external_port
        self.port_mapping_function = self.get_port_mapping_function()
        self.time_of_last_mapping = -float("inf")

        self.update()
        print(f"UPnP: First port forward rule set: {self.external_ip}:{self.external_port} -> {self.internal_ip}:{self.internal_port}")

    def get_port_mapping_function(self):
        upnp_api = upnpy.UPnP()
        upnp_api.discover()
        gateway_device: SSDPDevice = upnp_api.get_igd()
        actions: list[SSDPDevice.Service.Action] = flatten_list([s.get_actions() for s in gateway_device.get_services()])

        for action in actions:
            if action.name == "AddPortMapping":
                print(f"UPnP: Selected port forwarding action: {gateway_device}/{action.service}/{action}")
                return action

        raise Exception("No actions for port forwarding")

    def update(self):
        now = time.time()
        if now < self.time_of_last_mapping + RULE_UPDATE_DELAY_SECONDS:
            return
        else:
            self.time_of_last_mapping = now

        self.port_mapping_function(
            NewRemoteHost = '',
            NewExternalPort = self.external_port,
            NewProtocol = 'UDP',
            NewInternalPort = self.internal_port,
            NewInternalClient = self.internal_ip,
            NewEnabled = 1,
            NewPortMappingDescription = 'Pyshooter server',
            NewLeaseDuration = MAPPING_RULE_DURATION_SECONDS
        )
