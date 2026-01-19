# config/logging_config.py
LOGGING_CONFIG = {
    "console": True,
    "logdir": "./logs",
    "success_logfile": "success.log",
    "fail_logfile": "fail.log",
    "success_level": "INFO", # DEBUG, INFO, WARNING, ERROR, CRITICAL
    "fail_level": "ERROR",
    "rotation": {
        "when": "M",           # Options: 'S', 'M', 'H', 'D', 'midnight', 'W0'–'W6'
        "interval": 5,
        "backupCount": 10
    },
    "log_type": "both", # Options: fail_only, success_only, both
    "mode": "both", # Options: master, module, both
    "capture_warning": False,
    "trace": True,
}
