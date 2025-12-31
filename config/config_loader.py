import configparser, os
from pathlib import Path
from core.logging_manager import setup_loggers

success_logger, fail_logger = setup_loggers(logger_name="config_loader")

CONFIG_FILE = "config/config.ini"
_config_cache = None

def _get_config():
    global _config_cache
    if _config_cache is None:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        _config_cache = config
    return _config_cache


def load_account_config():
    account_config_file = None
    try:
        config = _get_config()
        account_config_file = config["account"].get("account_config_file")
    except KeyError:
        pass

    account_config_file = account_config_file or os.environ.get("ACCOUNT_CONFIG_FILE")

    if not account_config_file:
        fail_logger.error(f"{CONFIG_FILE} missing [account] section and ACCOUNT_CONFIG_FILE env var not set")
        account_config_file = input("Enter path to account config file: ")

    return Path(account_config_file).expanduser()


def load_nagios_config():
    nagios_config_file = None
    try:
        config = _get_config()
        nagios_config_file = config["nagios"].get("nagios_config_file")
    except KeyError:
        pass

    nagios_config_file = nagios_config_file or os.environ.get("NAGIOS_CONFIG_FILE")

    if not nagios_config_file:
        fail_logger.error(f"{CONFIG_FILE} missing [nagios] section and NAGIOS_CONFIG_FILE env var not set")
        nagios_config_file = input("Enter path to nagios config file: ")

    return Path(nagios_config_file).expanduser()


def load_backup_config():
    backup_dir = None
    try:
        config = _get_config()
        backup_dir = config["gitrepo"].get("backup_dir")
    except KeyError:
        pass

    backup_dir = backup_dir or os.environ.get("BACKUP_DIR")

    if not backup_dir:
        fail_logger.error(f"{CONFIG_FILE} missing [gitrepo] section and BACKUP_DIR env var not set")
        backup_dir = input("Enter path to backup directory: ")

    return Path(backup_dir).expanduser()


def load_cisco_eox_config():
    """
    Load Cisco EoX config file path with precedence:
    1. config/config.ini
    2. environment variable CISCO_EOX_CONFIG_FILE
    3. prompt user
    """
    eox_config_file = None
    try:
        config = _get_config()
        eox_config_file = config["cisco_eox"].get("cisco_eox_config_file")
    except KeyError:
        pass

    eox_config_file = eox_config_file or os.environ.get("CISCO_EOX_CONFIG_FILE")

    if not eox_config_file:
        fail_logger.error(
            f"{CONFIG_FILE} missing [cisco_eox] section and CISCO_EOX_CONFIG_FILE env var not set"
        )
        eox_config_file = input("Enter path to Cisco EoX config file: ")

    return Path(eox_config_file).expanduser()


def load_device_management_config():
    config_folder = None
    operational_folder = None

    try:
        config = _get_config()
        section = config["data_for_device_management"]

        config_folder = section.get("config_folder")
        operational_folder = section.get("operational_folder")

    except KeyError:
        # Section missing or keys missing — handled below
        pass

    # Allow environment variable overrides
    config_folder = config_folder or os.environ.get("CONFIG_FOLDER")
    operational_folder = operational_folder or os.environ.get("OPERATIONAL_FOLDER")

    # If still missing, prompt user interactively
    if not config_folder:
        fail_logger.error(
            f"{CONFIG_FILE} missing [data_for_device_management] config_folder "
            "and CONFIG_FOLDER env var not set"
        )
        config_folder = input("Enter path to config folder: ")

    if not operational_folder:
        fail_logger.error(
            f"{CONFIG_FILE} missing [data_for_device_management] operational_folder "
            "and OPERATIONAL_FOLDER env var not set"
        )
        operational_folder = input("Enter path to operational data folder: ")

    return {
        "config_folder": Path(config_folder).expanduser(),
        "operational_folder": Path(operational_folder).expanduser(),
    }
