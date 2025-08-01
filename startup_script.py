import os
import subprocess
import time
import re
import requests
from pathlib import Path

# removed sudo commands to allow auto start at boot
# Configs
NGROK_TOKEN = "YOUR_NGROK_TOKEN_HERE"
NGROK_IMAGE = "ngrok/ngrok:latest"
NGROK_PORT = "5678"
CONTAINER_NAME = "ngrok-n8n"
COMPOSE_FILE = Path("/home/{user_name}/n8n-docker/docker-compose.yml")

def run_ngrok_container():
    print("[*] Launching ngrok container in background...")
    subprocess.run(["sudo", "docker", "rm", "-f", CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.run([
        "docker", "run", "-d",
        "--net=host",  # exposes localhost:4040 API
        "--name", CONTAINER_NAME,
        "-e", f"NGROK_AUTHTOKEN={NGROK_TOKEN}",
        NGROK_IMAGE,
        "http", NGROK_PORT
    ], check=True)

    print("[+] ngrok container started.")

def get_ngrok_url():
    print("[*] Querying ngrok local API for tunnel URL...")
    for _ in range(20):
        try:
            response = requests.get("http://127.0.0.1:4040/api/tunnels")
            tunnels = response.json().get("tunnels", [])
            for tunnel in tunnels:
                if tunnel["proto"] == "https":
                    print(f"[+] Found ngrok HTTPS URL: {tunnel['public_url']}")
                    return tunnel["public_url"]
        except Exception:
            pass
        time.sleep(0.5)

    print("[!] ngrok tunnel URL not found in API, check Internet Connection.")
    subprocess.run(["sudo", "docker", "logs", CONTAINER_NAME])
    exit(1)

def update_docker_compose(ngrok_url):
    print("[*] Updating docker-compose.yml...")
    if not COMPOSE_FILE.exists():
        print(f"[!] Compose file not found: {COMPOSE_FILE}")
        exit(1)

    new_host = ngrok_url.replace("https://", "")
    updated_lines = []

    with open(COMPOSE_FILE, "r") as f:
        for line in f:
            if "WEBHOOK_URL=" in line:
                line = re.sub(r'WEBHOOK_URL=https://[^\s]+', f"WEBHOOK_URL={ngrok_url}", line)
            elif "N8N_HOST=" in line:
                line = re.sub(r'N8N_HOST=[^\s]+', f"N8N_HOST={new_host}", line)
            updated_lines.append(line)

    with open(COMPOSE_FILE, "w") as f:
        f.writelines(updated_lines)

    print("[+] Compose file updated.")

def restart_docker_compose():
    print("[*] Restarting Docker Compose...")
    subprocess.run(["docker-compose", "down"], cwd=COMPOSE_FILE.parent)
    subprocess.run(["docker-compose", "up", "-d"], cwd=COMPOSE_FILE.parent)
    print("[+] Docker services restarted.")

def main():
    print("==== Arcanum NGROK Auto-Updater v3 ====")
    run_ngrok_container()
    ngrok_url = get_ngrok_url()
    update_docker_compose(ngrok_url)
    restart_docker_compose()

if __name__ == "__main__":
    main()
