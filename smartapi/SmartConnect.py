
import requests
from .api_constants import BASE_URL

class SmartConnect:
    def __init__(self, api_key):
        self.api_key = api_key
        self.jwt_token = None
        self.refresh_token = None

    def generateSessionV2(self, client_id, mpin, totp):
        url = f"{BASE_URL}/rest/auth/angelbroking/user/v2/loginByMpin"
        payload = {
            "clientcode": client_id,
            "mpin": mpin,
            "totp": totp
        }
        headers = {"X-PrivateKey": self.api_key}
        resp = requests.post(url, json=payload, headers=headers)
        return resp.json()

    def setAccessToken(self, token):
        self.jwt_token = token

    def setRefreshToken(self, token):
        self.refresh_token = token
