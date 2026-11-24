"""Minimal UPnP IGD client (stdlib only).

Purpose: on a router without credentials, discover the Internet Gateway Device,
report the WAN address (to detect CGNAT) and optionally add a port mapping
internally -> external so the attendance server is reachable from the internet.

Usage:
    python upnp_portmap.py                 # discover + show WAN IP
    python upnp_portmap.py --map 8000      # also map internal 8000 -> external 8000
    python upnp_portmap.py --unmap 8000
"""
from __future__ import annotations

import argparse
import re
import socket
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

SSDP_ADDR = ("239.255.255.250", 1900)
SEARCH_TARGETS = [
    "urn:schemas-upnp-org:device:InternetGatewayDevice:1",
    "urn:schemas-upnp-org:service:WANIPConnection:1",
    "urn:schemas-upnp-org:service:WANPPPConnection:1",
]


def ssdp_discover(timeout: float = 4.0) -> list[str]:
    locations: list[str] = []
    for target in SEARCH_TARGETS:
        msg = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {SSDP_ADDR[0]}:{SSDP_ADDR[1]}\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 3\r\n"
            f"ST: {target}\r\n\r\n"
        ).encode()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(timeout)
        try:
            sock.sendto(msg, SSDP_ADDR)
            while True:
                try:
                    data, _ = sock.recvfrom(65507)
                except socket.timeout:
                    break
                text = data.decode("utf-8", "replace")
                m = re.search(r"^LOCATION:\s*(\S+)", text, re.I | re.M)
                if m and m.group(1) not in locations:
                    locations.append(m.group(1))
        finally:
            sock.close()
    return locations


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def find_services(desc_url: str) -> list[dict]:
    base = urlparse(desc_url)
    with urllib.request.urlopen(desc_url, timeout=8) as r:
        root = ET.fromstring(r.read())
    found = []
    for svc in root.iter():
        if _local(svc.tag) != "service":
            continue
        stype = svc.findtext("{*}serviceType") or ""
        if "WANIPConnection" in stype or "WANPPPConnection" in stype:
            ctrl = svc.findtext("{*}controlURL") or ""
            found.append(
                {
                    "type": stype,
                    "control": urljoin(f"{base.scheme}://{base.netloc}", ctrl),
                }
            )
    return found


def soap(control_url: str, service_type: str, action: str, body: str = "") -> str:
    env = (
        '<?xml version="1.0"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        f"<s:Body><u:{action} xmlns:u=\"{service_type}\">{body}</u:{action}></s:Body>"
        "</s:Envelope>"
    ).encode()
    req = urllib.request.Request(
        control_url,
        data=env,
        headers={
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": f'"{service_type}#{action}"',
            "Connection": "close",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode("utf-8", "replace")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", type=int, metavar="PORT")
    ap.add_argument("--unmap", type=int, metavar="PORT")
    ap.add_argument("--internal-ip", default="192.168.1.13")
    args = ap.parse_args()

    locs = ssdp_discover()
    if not locs:
        print("NO_UPNP_DEVICE_FOUND")
        return 2
    print("descriptions:", locs)

    services: list[dict] = []
    for loc in locs:
        try:
            services += find_services(loc)
        except Exception as exc:  # noqa: BLE001
            print("  ! failed to read", loc, exc)
    if not services:
        print("NO_WAN_SERVICE_FOUND")
        return 3
    print("wan services:", [s["type"] for s in services])
    svc = services[0]

    try:
        out = soap(svc["control"], svc["type"], "GetExternalIPAddress")
        ip = re.search(r"<NewExternalIPAddress>([^<]*)<", out)
        print("WAN_IP:", ip.group(1) if ip else "unknown")
    except Exception as exc:  # noqa: BLE001
        print("GetExternalIPAddress failed:", exc)

    try:
        out = soap(
            svc["control"],
            svc["type"],
            "GetStatusInfo",
        )
        m = re.search(r"<NewConnectionStatus>([^<]*)<", out)
        print("CONNECTION_STATUS:", m.group(1) if m else "unknown")
    except Exception as exc:  # noqa: BLE001
        print("GetStatusInfo failed:", exc)

    if args.unmap:
        body = (
            "<NewRemoteHost></NewRemoteHost>"
            f"<NewExternalPort>{args.unmap}</NewExternalPort>"
            "<NewProtocol>TCP</NewProtocol>"
        )
        print("unmap:", soap(svc["control"], svc["type"], "DeletePortMapping", body)[:200])

    if args.map:
        body = (
            "<NewRemoteHost></NewRemoteHost>"
            f"<NewExternalPort>{args.map}</NewExternalPort>"
            "<NewProtocol>TCP</NewProtocol>"
            f"<NewInternalPort>{args.map}</NewInternalPort>"
            f"<NewInternalClient>{args.internal_ip}</NewInternalClient>"
            "<NewEnabled>1</NewEnabled>"
            "<NewPortMappingDescription>HozoorYar</NewPortMappingDescription>"
            "<NewLeaseDuration>0</NewLeaseDuration>"
        )
        try:
            print("map:", soap(svc["control"], svc["type"], "AddPortMapping", body)[:200])
            print("MAPPING_OK")
        except Exception as exc:  # noqa: BLE001
            print("MAPPING_FAILED:", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
