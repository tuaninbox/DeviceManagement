import os
import time
import requests
import configparser
from requests_ntlm import HttpNtlmAuth
from ratelimit import limits, sleep_and_retry
from config.config_loader import load_cisco_eox_config

class CiscoEoxClient:
    def __init__(self, client_id, client_secret, proxy_url, proxy_user, proxy_pass):
        self.client_id = client_id
        self.client_secret = client_secret
        self.proxies = {"http": proxy_url, "https": proxy_url}
        self.proxy_auth = HttpNtlmAuth(proxy_user, proxy_pass)

        # Load API parameters from external Cisco EoX config file
        filename = os.path.expanduser(load_cisco_eox_config())
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Cisco EoX config file not found: {filename}")

        config = configparser.ConfigParser()
        config.read(filename)

        if "api" not in config:
            raise KeyError(f"{filename} missing [api] section")

        api_section = config["api"]
        self.token_url = api_section.get("token_url")
        self.coverage_url = api_section.get("coverage_url")
        self.rate_limit_calls = api_section.getint("rate_limit_calls", fallback=10)
        self.rate_limit_period = api_section.getint("rate_limit_period", fallback=1)

        self.access_token = None
        self.token_expiry = 0  # epoch seconds

    def _refresh_token(self):
        resp = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            proxies=self.proxies,
            auth=self.proxy_auth,
        )
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.token_expiry = time.time() + int(data.get("expires_in", 3600)) - 30

    def _get_token(self):
        if not self.access_token or time.time() >= self.token_expiry:
            self._refresh_token()
        return self.access_token

    def query_serial(self, sn: str):
        """
        Query Cisco EoX API for a serial number, respecting dynamic rate limits.
        """
        @sleep_and_retry
        @limits(calls=self.rate_limit_calls, period=self.rate_limit_period)
        def _inner():
            token = self._get_token()
            resp = requests.get(
                self.coverage_url.format(sn=sn),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                proxies=self.proxies,
                auth=self.proxy_auth,
            )
            resp.raise_for_status()
            return resp.json()

        return _inner()
