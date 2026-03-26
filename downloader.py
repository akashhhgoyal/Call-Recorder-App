import streamlit as st
import requests
import time
import base64

# ================= CONFIG =================
CLIENT_ID = st.secrets["genesys"]["GENESYS_CLIENT_ID"]
CLIENT_SECRET = st.secrets["genesys"]["GENESYS_CLIENT_SECRET"]
REGION = st.secrets["genesys"]["GENESYS_REGION"]

TOKEN_ENDPOINT = f"https://login.{REGION}.pure.cloud/oauth/token"
METADATA_URL = f"https://api.{REGION}.pure.cloud/api/v2/conversations/{{conversation_id}}/recordingmetadata"
MEDIA_URL = f"https://api.{REGION}.pure.cloud/api/v2/conversations/{{conversation_id}}/recordings/{{recording_id}}"

# ================= TOKEN =================
def get_token():
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {"grant_type": "client_credentials"}

    response = requests.post(TOKEN_ENDPOINT, headers=headers, data=data, timeout=30)

    if response.status_code != 200:
        raise Exception(f"Token Error: {response.text}")

    return response.json()["access_token"]


# ================= METADATA =================
def get_audio_id(conversation_id, headers):
    url = METADATA_URL.format(conversation_id=conversation_id)

    r = requests.get(url, headers=headers, timeout=30)

    if r.status_code != 200:
        raise Exception(f"Metadata Error: {r.status_code} - {r.text}")

    try:
        data = r.json()
    except:
        raise Exception(f"Invalid Metadata JSON: {r.text}")

    audio_id = next(
        (item['id'] for item in data if item.get('media') == 'audio'),
        None
    )

    if not audio_id:
        raise Exception("No audio recording found")

    return audio_id


# ================= SINGLE CHANNEL =================
def download_single(conversation_id, audio_id, headers):

    url = MEDIA_URL.format(
        conversation_id=conversation_id,
        recording_id=audio_id
    ) + "?formatId=WAV&download=true"

    r = requests.get(url, headers=headers, timeout=30)

    if r.status_code != 200:
        raise Exception(f"Single Media Error: {r.status_code} - {r.text}")

    try:
        data = r.json()
    except:
        raise Exception(f"Invalid JSON (single): {r.text}")

    if "mediaUris" not in data or "S" not in data["mediaUris"]:
        raise Exception(f"Recording not ready: {data}")

    media_url = data["mediaUris"]["S"]["mediaUri"]

    audio = requests.get(media_url, headers=headers, timeout=120)
    audio.raise_for_status()

    return audio.content


# ================= DUAL CHANNEL =================
def get_dual_media(url, headers, retries=12, wait=5):

    for i in range(retries):
        r = requests.get(url, headers=headers, timeout=30)

        print(f"Attempt {i+1}: Status {r.status_code}")

        if r.status_code == 200:
            try:
                data = r.json()

                media = data.get("mediaUris", {})
                url0 = media.get("0", {}).get("mediaUri")
                url1 = media.get("1", {}).get("mediaUri")

                if url0 and url1:
                    return url0, url1

            except Exception:
                print("Not JSON yet:", r.text)

        elif r.status_code == 202:
            print("Recording still processing...")

        else:
            print("Error response:", r.text)

        time.sleep(wait)

    raise Exception("Dual channel recording not ready after retries")


def download_dual(conversation_id, audio_id, headers):

    url = MEDIA_URL.format(
        conversation_id=conversation_id,
        recording_id=audio_id
    ) + "?formatId=WAV&download=false"

    url0, url1 = get_dual_media(url, headers)

    audio0 = requests.get(url0, headers=headers, timeout=120)
    audio1 = requests.get(url1, headers=headers, timeout=120)

    audio0.raise_for_status()
    audio1.raise_for_status()

    return {
        "customer": audio0.content,
        "agent": audio1.content
    }


# ================= MAIN FUNCTION =================
def run_downloader(conversation_id, channel_type):

    try:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}

        audio_id = get_audio_id(conversation_id, headers)

        if channel_type == "Single Channel":
            data = download_single(conversation_id, audio_id, headers)
        else:
            data = download_dual(conversation_id, audio_id, headers)

        return True, data

    except Exception as e:
        return False, str(e)