import requests

# ✅ Step 1: Configure your credentials here
FAXAGE_CREDENTIALS = {
    "username": "akumar",
    "password": "@Faxage123!",
    "company": "110686",
}

FAXAGE_API_URL = "https://api.faxage.com/httpsfax.php"

# ✅ Step 2: Get all fax IDs using listfax
def list_fax_ids():
    payload = {
        **FAXAGE_CREDENTIALS,
        "operation": "listfax"
    }

    try:
        response = requests.post(FAXAGE_API_URL, data=payload)
        response.raise_for_status()

        lines = response.text.strip().splitlines()
        fax_ids = [line.split()[0] for line in lines if line.split()[0].isdigit()]
        print(f"📥 Found {len(fax_ids)} faxes.")
        return fax_ids

    except Exception as e:
        print(f"❌ Error fetching fax list: {e}")
        return []


# ✅ Step 3: Mark each fax as unread (handled=0)
def mark_faxes_as_unread(fax_ids):
    for recvid in fax_ids:
        payload = {
            **FAXAGE_CREDENTIALS,
            "operation": "handled",
            "recvid": recvid,
            "handled": "1"
        }

        try:
            response = requests.post(FAXAGE_API_URL, data=payload)
            print("response : :::",response.json)
            if response.status_code == 200 and "marked unhandled" in response.text:
                print(f"🔄 Marked fax {recvid} as UNREAD")
            else:
                print(f"⚠️ Could not mark {recvid} as unread: {response.text.strip()}")
        except Exception as e:
            print(f"❌ Error marking fax {recvid} as unread: {e}")


if __name__ == "__main__":
    fax_ids = list_fax_ids()
    if fax_ids:
        mark_faxes_as_unread(fax_ids)
