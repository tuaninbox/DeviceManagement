from config.auth_loader import (
    get_auth_mode,
    get_ldap_config,
    get_oidc_config,
)

from .ldap_auth import LDAPAuth
from .oidc_auth import OIDCAuth
from .local_auth import LocalAuth


def get_auth_provider():
    mode = get_auth_mode()

    if mode == "ldap":
        cfg = get_ldap_config()
        return LDAPAuth(
            server_url=cfg["server_url"],
            domain=cfg["domain"],
            base_dn=cfg["base_dn"],
        )

    if mode == "oidc":
        cfg = get_oidc_config()
        return OIDCAuth(
            issuer=cfg["issuer"],
            client_id=cfg["client_id"],
        )
    
    if mode == "local":
        return LocalAuth()

    raise Exception(f"Unknown auth mode: {mode}")
