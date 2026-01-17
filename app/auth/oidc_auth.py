import requests
from jose import jwt, jwk
from jose.utils import base64url_decode
from .base_auth import AuthProvider
from .role_mapping_loader import ROLE_MAPPING


class OIDCAuth(AuthProvider):
    def __init__(self, issuer: str, client_id: str):
        self.issuer = issuer
        self.client_id = client_id

        # Load provider metadata
        metadata_url = f"{issuer}/.well-known/openid-configuration"
        metadata = requests.get(metadata_url).json()

        self.jwks_uri = metadata["jwks_uri"]
        self.jwks = requests.get(self.jwks_uri).json()

    def authenticate(self, token: str):
        claims = self._verify_token(token)

        username = claims.get("preferred_username") or claims.get("email")
        if not username:
            return None

        oidc_groups = claims.get("groups", [])
        roles = self._map_claims_to_roles(oidc_groups)

        return {
            "username": claims["preferred_username"],
            "roles": mapped_roles,
            "full_name": claims.get("name"),
            "email": claims.get("email")
        }
            

    def _verify_token(self, token: str):
        headers = jwt.get_unverified_header(token)
        kid = headers["kid"]

        # Find matching key
        key = next((k for k in self.jwks["keys"] if k["kid"] == kid), None)
        if not key:
            raise Exception("OIDC key not found")

        public_key = jwk.construct(key)

        message, encoded_sig = token.rsplit(".", 1)
        decoded_sig = base64url_decode(encoded_sig.encode())

        if not public_key.verify(message.encode(), decoded_sig):
            raise Exception("Invalid token signature")

        claims = jwt.get_unverified_claims(token)

        # Validate issuer and audience
        if claims["iss"] != self.issuer:
            raise Exception("Invalid issuer")

        if self.client_id not in claims["aud"]:
            raise Exception("Invalid audience")

        return claims

    def _map_claims_to_roles(self, oidc_groups):
        roles = []
        oidc_mapping = ROLE_MAPPING.get("oidc", {})

        for role, claim_values in oidc_mapping.items():
            for value in claim_values:
                if value in oidc_groups:
                    roles.append(role)
                    break

        if "user" not in roles:
            roles.append("user")

        return roles
