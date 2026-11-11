#!/usr/bin/env python3
"""
AP Isolation Bypass for Linux
Bypasses AP isolation by routing local subnet traffic through the gateway.
Usage: sudo bypass_ap_isolation.py
"""

import subprocess
import sys
import struct
import socket
import re
import os


def get_default_gateway() -> str | None:
    """Get the default gateway IP."""
    try:
        result = subprocess.run(
            ['ip', 'route', 'show', 'default'],
            capture_output=True, text=True
        )
        for line in result.stdout.split('\n'):
            if line.strip().startswith('default'):
                match = re.search(r'via\s+(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    return match.group(1)
    except Exception as e:
        print(f"Error getting default gateway: {e}")
    return None


def get_network_interfaces() -> list[dict[str, str]]:
    """Get list of interfaces with IP addresses and netmasks."""
    interfaces: list[dict[str, str]] = []
    try:
        result = subprocess.run(
            ['ip', '-4', 'addr', 'show'],
            capture_output=True, text=True
        )
        output = result.stdout
    except FileNotFoundError:
        print("Error: 'ip' command not found.")
        sys.exit(1)

    current_iface: str | None = None
    for line in output.split('\n'):
        if re.match(r'^\d+: \w+:', line):
            match = re.search(r'^\d+: (\w+):', line)
            if match:
                current_iface = match.group(1)
        elif current_iface and 'inet ' in line:
            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)', line)
            if match:
                ip: str = match.group(1)
                cidr: int = int(match.group(2))
                mask_int: int = (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF
                netmask: str = socket.inet_ntoa(struct.pack("=I", mask_int))
                interfaces.append({
                    'ifname': current_iface,
                    'ip': ip,
                    'cidr': str(cidr),
                    'netmask': netmask
                })
                current_iface = None
    return interfaces


def calculate_network_id(ip: str, cidr: int) -> tuple[str, int]:
    """Calculate network ID given IP and CIDR."""
    ip_bytes = socket.inet_aton(ip)
    ip_int = int.from_bytes(ip_bytes, byteorder='big')
    mask_int: int = (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF
    network_int: int = ip_int & mask_int
    network_id: str = socket.inet_ntoa(struct.pack("!I", network_int))
    return network_id, mask_int


def add_route(network_id: str, cidr: int, gateway: str, iface: str) -> bool:
    """Add a route via the gateway."""
    # Delete existing route to prevent duplicates
    try:
        _ = subprocess.run([
            'ip', 'route', 'del', network_id, 'dev', iface
        ], capture_output=True, check=False)
    except subprocess.CalledProcessError:
        pass  # No previous route exists or already removed

    cmd: list[str] = ['ip', 'route', 'add', f'{network_id}/{cidr}', 'via', gateway, 'dev', iface]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("Route added successfully.")
            return True
        else:
            print(f"Error adding route: {result.stderr}")
    except Exception as e:
        print(f"Failed to add route: {e}")
    return False


def main() -> None:
    print("=" * 60)
    print("AP Isolation Bypass for Linux")
    print("=" * 60)
    print()

    # Check if running as root (sudo)
    if os.geteuid() != 0:
        print("ERROR: Please run this script with sudo/root privileges.")
        print("Run: sudo ./bypass_ap_isolation.py")
        sys.exit(1)

    # Get interfaces
    interfaces = get_network_interfaces()
    if not interfaces:
        print("No suitable network interface found.")
        sys.exit(1)

    print("Active interfaces:")
    default_gw = get_default_gateway()
    for i, iface in enumerate(interfaces):
        print(f"  [{i}] {iface['ifname']}")
        print(f"      IP: {iface['ip']}/{iface['cidr']}")
        print(f"      Netmask: {iface['netmask']}")
        if iface['ifname'] == default_gw:
            print(f"      Gateway: {default_gw}")
    print()

    # Select interface
    for i, iface in enumerate(interfaces):
        print(f"[{i}] {iface['ifname']}")
    print()

    while True:
        try:
            choice = input("Select interface [0-{}]:".format(len(interfaces) - 1))
            idx = int(choice)
            if 0 <= idx < len(interfaces):
                selected = interfaces[idx]
                break
        except ValueError:
            print("Please enter a number.")

    while True:
        gw = input("Enter gateway IP (or press Enter to use auto-detected): ").strip()
        if not gw:
            gw = default_gw
            if not gw:
                print("No gateway detected. Please provide gateway IP.")
                continue
            print("Using auto-detected gateway:", gw)
            break
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', gw):
            break
        print("Invalid gateway!")

    # Use /18 CIDR (255.255.192.0) as specified
    cidr: int = 18
    network_id, mask_int = calculate_network_id(selected['ip'], cidr)
    netmask_str = socket.inet_ntoa(struct.pack("=I", mask_int))
    print(f"\nNetwork: {network_id}/{cidr}")
    print(f"Netmask: {netmask_str}")

    # Apply route
    print(f"\nApplying route via {gw}...")
    if add_route(network_id, cidr, gw, selected['ifname']):
        print("\nConfiguration complete.")
        print("Note: AP isolation bypass implemented. Other devices on the same subnet")
        print("should now be able to communicate via the gateway.")
    else:
        print("Failed to configure route.")
        sys.exit(1)


if __name__ == '__main__':
    main()
