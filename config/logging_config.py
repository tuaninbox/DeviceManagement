# config/logging_config.py
LOGGING_CONFIG = {
    "console": True,
    "logdir": "./logs",
    "success_logfile": "success.log",
    "fail_logfile": "fail.log",
    "rotation": {
        "when": "M",           # Options: 'S', 'M', 'H', 'D', 'midnight', 'W0'–'W6'
        "interval": 5,
        "backupCount": 10
    },
    "log_type": "both", # Options: fail_only, success_only, both
    "mode": "both", # Options: master, module, both
}
