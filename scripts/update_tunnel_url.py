#!/usr/bin/env python3
import os
import re
import subprocess
import sys

def update_env_with_tunnel(tunnel_url):
    # Validate URL
    tunnel_url = tunnel_url.strip().rstrip('/')
    if not tunnel_url.startswith("https://"):
        print("Error: Tunnel URL must start with https://")
        return False
        
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, ".env")
    
    if not os.path.exists(env_path):
        print(f"Error: .env file not found at {env_path}")
        return False
        
    with open(env_path, 'r') as f:
        content = f.read()
        
    # Find current configured BACKEND_URL
    match = re.search(r'BACKEND_URL=([^\n]+)', content)
    if not match:
        print("Error: BACKEND_URL not found in .env")
        return False
        
    old_url = match.group(1).strip()
    print(f"Current configured URL in .env: {old_url}")
    print(f"New tunnel URL to apply: {tunnel_url}")
    
    # 1. Update primary URL fields
    content = re.sub(r'BACKEND_URL=[^\n]+', f'BACKEND_URL={tunnel_url}', content)
    content = re.sub(r'FRONTEND_URL=[^\n]+', f'FRONTEND_URL={tunnel_url}', content)
    content = re.sub(r'NEXT_PUBLIC_BACKEND_URL=[^\n]+', f'NEXT_PUBLIC_BACKEND_URL={tunnel_url}', content)
    content = re.sub(r'NEXT_PUBLIC_FRONTEND_URL=[^\n]+', f'NEXT_PUBLIC_FRONTEND_URL={tunnel_url}', content)
    
    # 2. Update OAuth Redirect URIs
    content = re.sub(r'MICROSOFT_REDIRECT_URI=[^\n]+', f'MICROSOFT_REDIRECT_URI={tunnel_url}/api/v1/auth/microsoft/callback', content)
    content = re.sub(r'GOOGLE_REDIRECT_URI=[^\n]+', f'GOOGLE_REDIRECT_URI={tunnel_url}/api/v1/auth/google/callback', content)
    
    with open(env_path, 'w') as f:
        f.write(content)
        
    print("\n[✓] Successfully updated .env configuration with new tunnel URL!")
    return True

def restart_containers():
    print("\nStarting docker compose update...")
    try:
        # Run docker compose up -d to apply new env vars
        subprocess.check_call(["docker", "compose", "up", "-d"])
        
        # Rebuild bot container since it has no volume mounts and contains baked-in urls
        print("\nRebuilding and restarting Telegram bot container...")
        subprocess.check_call(["docker", "compose", "up", "-d", "--build", "bot"])
        
        print("\n[✓] Docker stack is successfully updated and running!")
    except Exception as e:
        print(f"Error restarting docker containers: {e}")

if __name__ == "__main__":
    print("==================================================")
    print("   EmailAgg Tunnel Configurer & Container Updater   ")
    print("==================================================")
    print("This utility updates your .env and restarts Docker containers")
    print("with a secure public HTTPS tunnel URL for mobile testing.")
    print("==================================================\n")
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter your public HTTPS tunnel URL (e.g., https://xxx.ngrok-free.app): ").strip()
        
    if update_env_with_tunnel(url):
        restart_containers()
