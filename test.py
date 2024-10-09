import requests
from rich import print

BASE_URL = "http://localhost:8000/api"


def print_response(prefix, response):
    try:
        print(f"{prefix}: {response.json()}")
    except requests.exceptions.JSONDecodeError:
        print(f"{prefix}: {response.text}")


def test_create_invitation():
    url = f"{BASE_URL}/create-invitation/"
    print(url)
    response = requests.post(url)
    print_response("Create Invitation", response)
    invitation_code = response.json()["invitation_code"]
    return invitation_code


def test_generate_api_key(invitation_code):
    url = f"{BASE_URL}/generate-api-key/"
    print(url)
    response = requests.post(
        url, params={"invitation_code": invitation_code}
    )
    print_response("Generate API Key", response)
    if response.status_code == 400:
        print("Error: Invalid or already used invitation code")
        return None
    api_key = response.json()["api_key"]
    return api_key


def test_list_daemons(api_key):
    headers = {"X-API-KEY": api_key}
    url = f"{BASE_URL}/daemons/"
    print(url)
    response = requests.get(url, headers=headers)
    print_response("List Daemons", response)
    return response.json()


def test_start_daemon(api_key, daemon_name):
    headers = {"X-API-KEY": api_key}
    url = f"{BASE_URL}/daemons/{daemon_name}/start"
    print(url)
    response = requests.post(url, headers=headers)
    print_response("Start Daemon", response)
    return response.json()


def test_stop_daemon(api_key, daemon_name):
    headers = {"X-API-KEY": api_key}
    url = f"{BASE_URL}/daemons/{daemon_name}/stop"
    print(url)
    response = requests.post(url, headers=headers)
    print_response("Stop Daemon", response)
    return response.json()


if __name__ == "__main__":
    invitation_code = test_create_invitation()
    print(f"Invitation Code: {invitation_code}")

    api_token = test_generate_api_key(invitation_code)
    print(f"API Token: {api_token}")

    if api_token:
        daemons = test_list_daemons(api_token)
        if daemons and daemons.get("daemons"):
            daemon_name = daemons["daemons"][0]["name"]
            test_stop_daemon(api_token, daemon_name)
            test_start_daemon(api_token, daemon_name)

    print()
