import requests
import json
from .api_constants import BASE_URL

class SmartConnect:

    def __init__(self, api_key):
        self.api_key = api_key
        self.jwt_token = None
        self.refresh_token = None

        # Default header template for Angel One SmartAPI V2
        self.base_headers = {
            "Content-Type": "application/json",
            "X-PrivateKey": self.api_key,
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "Accept": "application/json",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "106.193.147.98",
            "X-MACAddress": "aa:bb:cc:dd:ee:ff"
        }

    def generateSessionV2(self, client_id, mpin, totp):
        url = f"{BASE_URL}/rest/auth/angelbroking/user/v1/loginByMpin"

        payload = {
            "clientcode": client_id,
            "mpin": mpin,
            "totp": totp
        }

        response = requests.post(url, json=payload, headers=self.base_headers)

        # Print raw output for debugging
        print("RAW LOGIN RESPONSE TEXT:", response.text)
        print("STATUS:", response.status_code)

        # Handle empty / non-JSON responses safely
        if response.text.strip() == "" or not response.text.strip().startswith("{"):
            raise Exception("Invalid response from SmartAPI server")

        data = response.json()

        if not data.get("status"):
            raise Exception(f"Login failed: {data.get('message')}")

        return data

    def setAccessToken(self, token):
        self.jwt_token = token

    def setRefreshToken(self, token):
        self.refresh_token = token
