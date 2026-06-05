#!/usr/bin/env python3
import os
import re
import socket
import subprocess
import sys

def get_local_ip():
    # Method 1: macOS specific ipconfig en0 (prioritize Wi-Fi)
    if sys.platform == "darwin":
        try:
            ip = subprocess.check_output(["ipconfig", "getifaddr", "en0"]).decode().strip()
            if ip and ip != "127.0.0.1":
                return ip
        except Exception:
            pass

    # Method 2: Check routing via UDP socket (best for multi-interface systems)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip != "127.0.0.1":
            return ip
    except Exception:
        pass

    # Method 3: macOS specific ipconfig other interfaces
    if sys.platform == "darwin":
        for interface in ["en1", "en2", "en3", "en4"]:
            try:
                ip = subprocess.check_output(["ipconfig", "getifaddr", interface]).decode().strip()
                if ip:
                    return ip
            except Exception:
                continue

    # Method 3: Standard hostname lookup
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and ip != "127.0.0.1":
            return ip
    except Exception:
        pass

    # Method 4: Fallback scan interfaces
    try:
        import array
        import struct
        import fcntl
        # Only works on Unix
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        max_possible = 8
        size = max_possible * 32
        names = array.array('B', b'\0' * size)
        outbytes = struct.unpack('i', fcntl.ioctl(
            s.fileno(),
            0x8912,  # SIOCGIFCONF
            struct.pack('iL', size, names.buffer_info()[0])
        ))[0]
        namestr = names.tobytes()
        for i in range(0, outbytes, 40):
            name = namestr[i:i+16].split(b'\0', 1)[0].decode()
            ip = socket.inet_ntoa(namestr[i+20:i+24])
            if ip != "127.0.0.1":
                return ip
    except Exception:
        pass

    return "127.0.0.1"

def update_env():
    # Resolve project root (parent of scripts directory)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, ".env")
    if not os.path.exists(env_path):
        print(f"Error: .env file not found at {env_path}")
        sys.exit(1)
        
    current_ip = get_local_ip()
    print(f"Detected current local IP: {current_ip}")
    
    with open(env_path, 'r') as f:
        content = f.read()
        
    # Find the current IP configured in BACKEND_URL
    match = re.search(r'BACKEND_URL=http://([^:/]+)', content)
    if not match:
        print("Warning: BACKEND_URL not found in .env, cannot determine configured IP.")
        return current_ip
        
    old_ip = match.group(1)
    print(f"Configured IP in .env: {old_ip}")
    
    if old_ip == current_ip:
        print("IP address has not changed. No update needed in .env.")
        return current_ip
        
    # Replace all occurrences of old_ip with current_ip
    new_content = content.replace(old_ip, current_ip)
    
    with open(env_path, 'w') as f:
        f.write(new_content)
        
    print(f"Successfully updated IP from {old_ip} to {current_ip} in .env")
    return current_ip

if __name__ == "__main__":
    update_env()
