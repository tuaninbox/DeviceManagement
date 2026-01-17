from config.auth_loader import (
    get_ldap_role_mapping,
    get_oidc_role_mapping,
)

ROLE_MAPPING = {
    "ldap": get_ldap_role_mapping(),
    "oidc": get_oidc_role_mapping(),
}
