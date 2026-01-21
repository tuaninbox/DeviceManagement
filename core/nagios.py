import requests
requests.packages.urllib3.disable_warnings()
import csv
from core.credentials import get_nagios_api
from config.config_loader import load_nagios_config

nagios_host, nagios_apikey = get_nagios_api()

def get_hostgroup_members_from_nagios(hostgroup_name):
    url = (
        f"https://{nagios_host}/nagiosxi/api/v1/objects/hostgroupmembers"
        f"?pretty=1&apikey={nagios_apikey}&hostgroup_name={hostgroup_name}"
    )
    r = requests.get(url, verify=False)
    return r.json().get("members", [])


def get_device_list_from_nagios(nagios_host=nagios_host, nagios_apikey=nagios_apikey):
    # Load hostgroups from config.ini
    cfg = load_nagios_config()
    hostgroups = cfg["hostgroups"]

    # ------------------------------------------------------------
    # 1. Build a set of all devices that belong to any hostgroup
    # ------------------------------------------------------------
    hostgroup_members = set()

    for hg in hostgroups:
        members = get_hostgroup_members_from_nagios(hg)
        for device in members:
            hostgroup_members.add(device.lower())

    # ------------------------------------------------------------
    # 2. Query all Nagios hosts
    # ------------------------------------------------------------
    url = (
        f"https://{nagios_host}/nagiosxi/api/v1/54342156/host"
        f"?pretty=1&apikey={nagios_apikey}&orderby=host_name:a"
    )
    r = requests.get(url, verify=False)
    devices = r.json()

    results = []

    # ------------------------------------------------------------
    # 3. Build inventory rows ONLY for devices in hostgroups
    # ------------------------------------------------------------
    for d in devices.get("host", []):
        original_hostname = d.get("host_name", "")
        hostname_key = original_hostname.lower()   # used only for matching

        if hostname_key not in hostgroup_members:
            continue

        results.append({
            "Host": original_hostname,             # preserve exact case
            "IP": d.get("address", ""),
            "Port": int(d.get("port", 22)),
            "Location": d.get("alias", ""),
            "Group": d.get("hostgroup_name", ""),
            "OS": "",                              # OS left blank for lazy detection
        })


    # ------------------------------------------------------------
    # 4. Optional CSV export
    # ------------------------------------------------------------
    with open("backup_devices.csv", "w", newline="") as csvfile:
        fieldnames = ["Host", "IP", "Port", "Location", "Group", "OS"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return results


if __name__ == "__main__":
    hostgroup_member = get_hostgroup_members_from_nagios("ConfigBackup")
    print(f"Hostgroup members: f{hostgroup_member}")
    devices = get_device_list_from_nagios()
    print(f"Device: {devices}")


# import requests
# from pathlib import Path
# from core.logging_manager import setup_loggers
# # import configparser
# from core.credentials import get_nagios_api
# # Initialize loggers for this module
# # success_logger, fail_logger = setup_loggers(logger_name="nagios")

# nagios_host, nagios_apikey = get_nagios_api()

# def get_device_list_from_nagios(nagios_host=nagios_host, nagios_apikey=nagios_apikey):
#     backup_device_list = [device.lower(0 for device in get_hostgroup_members_from_naigos("ConfigBackup")]
#     url = f"https://{nagios_host}/nagiosxi/api/v1/config/host?pretty=1&apikey={nagios_apikey}&orderby=host_name:a"
#     r = requests.get(url,verify=False)
#     devices = r.json()
#     results = []
#     for d in devices:
#         host_name = d.get("host_name", "").lower()
#         if host_name in backup_device_list:
#             results.append({
#                 "Host": d.get("host_name", ""),
#                 "IP": d.get("address", ""),          # Nagios JSON usually has 'address'
#                 "Port": "",                          # Leave empty
#                 "Location": d.get("alias", ""),      # Often 'alias' or custom field
#                 "Group": d.get("hostgroup_name", "") # Adjust if Nagios returns differently
#             })

#     # Write results to CSV
#     with open("backup_devices.csv", "w", newline="") as csvfile:
#         fieldnames = ["Host", "IP", "Port", "Location", "Group"]
#         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerows(results)

#     return results
#     return results

# def get_hostgroup_members_from_naigos(hostgroup_name):
#     url = f"https://{nagios_host}/nagiosxi/api/v1/config/hostgruops?pretty=1&apikey={nagios_apikey}&hostgroup_name={hostgroup_name}"
#     r = requests.get(url,verify=False)
#     return r.json()["members"]
    
# if __name__ == "__main__":
#     results = get_device_list_from_nagios()
#     print(results)