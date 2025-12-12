import requests
import json
from .api_constants import BASE_URL

class SmartConnect:

    def __init__(self, api_key):
        self.api_key = api_key
        self.jwt_token = None
        self.refresh_token = None

        self.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-PrivateKey": self.api_key,
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "Accept": "application/json",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "AA-BB-CC-11-22-33"
        }

    def generateSessionV2(self, client_id, mpin, totp):
        url = f"{BASE_URL}/rest/auth/angelbroking/user/v2/loginByMpin"

        payload = {
            "clientcode": client_id,
            "mpin": mpin,
            "totp": str(totp)
        }

        response = requests.post(url, json=payload, headers=self.headers)

        print("RAW LOGIN RESPONSE TEXT:", response.text)
        print("STATUS:", response.status_code)

        # Reject HTML responses (WAF block)
        if "<html>" in response.text.lower():
            raise Exception("Angel One WAF rejected the request. Headers/URL incorrect.")

        data = response.json()

        if not data.get("status"):
            raise Exception(f"Login failed: {data.get('message')}")

        # Set tokens
        self.jwt_token = data["data"]["jwtToken"]
        self.refresh_token = data["data"]["refreshToken"]

        return data

    def setAccessToken(self, token):
        self.jwt_token = token

    def setRefreshToken(self, token):
        self.refresh_token = token
