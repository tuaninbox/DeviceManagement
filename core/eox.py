from core.eox import CiscoEoxClient
from core.credentials import get_cisco_eox_credentials

def get_eox_data_from_sn(serials: list[str]) -> dict[str, dict]:
    """
    Query Cisco EoX API for a list of serial numbers.

    Args:
        serials: list of serial numbers to query

    Returns:
        dict mapping serial number -> EoX response data
    """
    # Load Cisco EoX credentials and proxy info
    creds = get_cisco_eox_credentials()

    # Initialize client using returned data
    client = CiscoEoxClient(
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        proxy_url=creds.get("proxy_url"),
        proxy_user=creds.get("proxy_user"),
        proxy_pass=creds.get("proxy_pass"),
    )

    results: dict[str, dict] = {}
    for sn in serials:
        data = client.query_serial(sn)
        results[sn] = data
        # print(f"{sn}: {data}")

    return results

if __name__ == "__main__":
    serials = ["", ""]
    results = get_eox_data_from_sn(serials)
    # results now holds a dict mapping serial → EoX response
    print("Final results:", results)
