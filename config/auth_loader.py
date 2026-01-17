import yaml
from pathlib import Path

def load_auth_config():
    yaml_path = Path(__file__).parent / "auth.yaml"
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)

AUTH_CONFIG = load_auth_config()

def get_auth_mode():
    return AUTH_CONFIG["auth"]["mode"]

def get_local_config():
    return AUTH_CONFIG.get("local", {})

def get_ldap_config():
    return AUTH_CONFIG.get("ldap", {})

def get_oidc_config():
    return AUTH_CONFIG.get("oidc", {})

def get_jwt_config():
    return AUTH_CONFIG.get("jwt", {})

def get_ldap_role_mapping():
    return AUTH_CONFIG.get("ldap", {}).get("roles", {})

def get_oidc_role_mapping():
    return AUTH_CONFIG.get("oidc", {}).get("roles", {})



