import os, getpass, configparser

from core.logging_manager import setup_loggers
from config.config_loader import load_account_config, load_cisco_eox_config, load_nagios_config

# Initialize loggers for this module
success_logger, fail_logger = setup_loggers(logger_name="credential")


def get_credentials():
    username = None
    password = None

    # Expand ~ to full path
    filename = os.path.expanduser(load_account_config())

    # 1. Try reading from credential file using configparser
    if os.path.exists(filename):
        config = configparser.ConfigParser()
        config.read(filename)

        if "credentials" in config:
            username = config["credentials"].get("username")
            password = config["credentials"].get("password")

    # 2. Fall back to environment variables
    if not username:
        username = os.environ.get("username")
    if not password:
        password = os.environ.get("password")

    # 3. Prompt user if still missing
    if not username:
        username = input("Enter username: ")
    if not password:
        password = getpass.getpass("Enter password: ")

    return username, password

def get_nagios_api():
    nagios_host = None
    nagios_apikey = None

    # Expand ~ to full path
    cfg = load_nagios_config()
    filename = cfg["config_file"]


    # 1. Try reading from credential file using configparser
    if os.path.exists(filename):
        config = configparser.ConfigParser()
        config.read(filename)

        if "nagios" in config:
            nagios_host = config["nagios"].get("nagios_host")
            nagios_apikey = config["nagios"].get("nagios_apikey")

    # 2. Fall back to environment variables
    if not nagios_host:
        nagios_host = os.environ.get("nagios_host")
    if not nagios_apikey:
        nagios_apikey = os.environ.get("nagios_apikey")

    # 3. Prompt user if still missing
    if not nagios_host:
        nagios_host = input("Enter Nagios Host: ")
    if not nagios_apikey:
        nagios_apikey = getpass.getpass("Enter Nagios APIKey: ")

    return nagios_host, nagios_apikey

def get_cisco_eox_credentials():
    """
    Load Cisco EoX API credentials (client_id/client_secret, proxy info).
    """
    client_id = None
    client_secret = None
    proxy_url = None
    proxy_user = None
    proxy_pass = None

    filename = os.path.expanduser(load_cisco_eox_config())

    if os.path.exists(filename):
        config = configparser.ConfigParser()
        config.read(filename)

        if "cisco_eox" in config:
            client_id = config["cisco_eox"].get("client_id")
            client_secret = config["cisco_eox"].get("client_secret")
            proxy_url = config["cisco_eox"].get("proxy_url")
            proxy_user = config["cisco_eox"].get("proxy_user")
            proxy_pass = config["cisco_eox"].get("proxy_pass")

    # Fall back to environment variables
    client_id = client_id or os.environ.get("CISCO_EOX_CLIENT_ID")
    client_secret = client_secret or os.environ.get("CISCO_EOX_CLIENT_SECRET")
    proxy_url = proxy_url or os.environ.get("CISCO_EOX_PROXY_URL")
    proxy_user = proxy_user or os.environ.get("CISCO_EOX_PROXY_USER")
    proxy_pass = proxy_pass or os.environ.get("CISCO_EOX_PROXY_PASS")

    # Prompt if still missing
    if not client_id:
        client_id = input("Enter Cisco EoX client_id: ")
    if not client_secret:
        client_secret = getpass.getpass("Enter Cisco EoX client_secret: ")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "proxy_url": proxy_url,
        "proxy_user": proxy_user,
        "proxy_pass": proxy_pass,
    }


if __name__=="__main__":
    print(get_credentials())