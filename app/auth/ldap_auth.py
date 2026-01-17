from ldap3 import Server, Connection, ALL, SUBTREE
from .base_auth import AuthProvider
from .role_mapping_loader import ROLE_MAPPING


class LDAPAuth(AuthProvider):
    def __init__(self, server_url: str, domain: str, base_dn: str):
        self.server = Server(server_url, get_info=ALL)
        self.domain = domain
        self.base_dn = base_dn

    def authenticate(self, username: str, password: str):
        user_dn = f"{self.domain}\\{username}"

        try:
            conn = Connection(
                self.server,
                user=user_dn,
                password=password,
                auto_bind=True
            )
        except Exception:
            return None

        # Search for user entry
        search_filter = f"(sAMAccountName={username})"
        conn.search(
            search_base=self.base_dn,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=["memberOf"]
        )

        if not conn.entries:
            return None

        entry = conn.entries[0]
        ldap_groups = entry.memberOf.values if "memberOf" in entry else []

        roles = self._map_groups_to_roles(ldap_groups)

        return {
            "username": ldap_username,
            "roles": mapped_roles,
            "full_name": ldap_full_name,
            "email": ldap_email
        }


    def _map_groups_to_roles(self, ldap_groups):
        roles = []
        ldap_mapping = ROLE_MAPPING.get("ldap", {})

        # Normalize LDAP groups for case-insensitive matching
        normalized_groups = [g.lower() for g in ldap_groups]

        for role, group_dns in ldap_mapping.items():
            for group_dn in group_dns:
                group_dn_lower = group_dn.lower()
                if any(group_dn_lower in g for g in normalized_groups):
                    roles.append(role)
                    break  # No need to check more groups for this role

        # Ensure basic role
        if "user" not in roles:
            roles.append("user")

        return roles
