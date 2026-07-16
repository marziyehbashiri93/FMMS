"""بارگذاری تنظیمات اتصال به SAP از فایل config.ini"""

import configparser
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")


def load_config():
    parser = configparser.ConfigParser()
    if not parser.read(CONFIG_PATH, encoding="utf-8"):
        raise FileNotFoundError(f"فایل config.ini یافت نشد: {CONFIG_PATH}")

    sap = parser["SAP"]

    protocol = sap.get("protocol", "https").strip().lower()
    instance = sap.get("instance", "00").strip()
    port = sap.get("port", "").strip()

    if not port:
        instance_num = int(instance)
        port = str(8000 + instance_num) if protocol == "http" else str(44300 + instance_num)

    username = sap.get("username", "").strip()
    password = sap.get("password", "").strip()
    if not username or not password:
        raise ValueError(
            "username و password در config.ini خالی است. لطفا آن‌ها را تکمیل کنید."
        )

    return {
        "host": sap.get("host", "").strip(),
        "system_id": sap.get("system_id", "").strip(),
        "protocol": protocol,
        "port": port,
        "client": sap.get("client", "").strip(),
        "verify_ssl": sap.getboolean("verify_ssl", fallback=False),
        "username": username,
        "password": password,
        "service": sap.get("service", "API_EQUIPMENT_SRV").strip(),
        "entity_set": sap.get("entity_set", "A_Equipment").strip(),
    }
