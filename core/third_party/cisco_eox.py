import os
import time
import json
import requests
import subprocess
import configparser
from ratelimit import limits, sleep_and_retry
from config.config_loader import load_cisco_eox_config

class CiscoEoxClientCntlm:
    def __init__(self, client_id, client_secret, proxy_url="http://127.0.0.1:3128"):
        self.client_id = client_id
        self.client_secret = client_secret

        # Build a session that uses cntlm as local proxy
        self.session = requests.Session()
        if proxy_url:
            self.session.proxies = {"http": proxy_url, "https": proxy_url}
        # No NTLM auth here — cntlm handles it

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
        resp = self.session.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
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
            resp = self.session.get(
                self.coverage_url.format(sn=sn),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            return resp.json()

        return _inner()

 
class CiscoEoxClient:
    def __init__(self, client_id, client_secret, proxy_url=None, proxy_user=None, proxy_pass=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.proxy_url = proxy_url
        self.proxy_user = proxy_user
        self.proxy_pass = proxy_pass

        # Load API parameters
        filename = os.path.expanduser(load_cisco_eox_config())
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Cisco EoX config file not found: {filename}")

        config = configparser.ConfigParser()
        config.read(filename)
        api_section = config["api"]

        self.token_url = api_section.get("token_url")
        self.coverage_url = api_section.get("coverage_url")
        self.rate_limit_calls = api_section.getint("rate_limit_calls", fallback=2)
        self.rate_limit_period = api_section.getint("rate_limit_period", fallback=1)
        self.access_token = None
        self.token_expiry = 0

    def _curl(self, args, data=None, headers=None):
        cmd = ["curl", "-sS"]

        # Proxy with NTLM
        if self.proxy_url and self.proxy_user and self.proxy_pass:
            cmd += ["--proxy", self.proxy_url,
                    "--proxy-ntlm",
                    "--proxy-user", f"{self.proxy_user}:{self.proxy_pass}"]

        # Headers
        if headers:
            for k, v in headers.items():
                cmd += ["-H", f"{k}: {v}"]

        # Data
        if data:
            cmd += ["--data-urlencode", f"grant_type={data['grant_type']}",
                    "--data-urlencode", f"client_id={data['client_id']}",
                    "--data-urlencode", f"client_secret={data['client_secret']}"]

        cmd.append(args)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"curl failed: {result.stderr}")
        return json.loads(result.stdout)

    def _refresh_token(self):
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        resp = self._curl(self.token_url, data=data,
                          headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.access_token = resp["access_token"]
        self.token_expiry = time.time() + int(resp.get("expires_in", 3600)) - 30

    def _get_token(self):
        if not self.access_token or time.time() >= self.token_expiry:
            self._refresh_token()
        return self.access_token

    def query_serial(self, sn: str):
        @sleep_and_retry
        @limits(calls=self.rate_limit_calls, period=self.rate_limit_period)
        def _inner():
            token = self._get_token()
            url = self.coverage_url.format(sn=sn)
            resp = self._curl(url, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            })
            return resp
        return _inner()


