"""کلاینت ساده برای فراخوانی سرویس OData مربوط به API_EQUIPMENT در SAP"""

import requests
import urllib3

from config import load_config


def build_base_url(cfg):
    return (
        f"{cfg['protocol']}://{cfg['host']}:{cfg['port']}"
        f"/sap/opu/odata/sap/{cfg['service']}/{cfg['entity_set']}"
    )


def get_equipment(top=50, skip=0, search=None, timeout=30):
    """داده‌های Equipment را از OData فراخوانی و لیستی از دیکشنری‌ها برمی‌گرداند"""

    cfg = load_config()
    url = build_base_url(cfg)

    params = {
        "sap-client": cfg["client"],
        "$format": "json",
        "$top": top,
        "$skip": skip,
    }

    if search:
        safe_search = search.replace("'", "''")
        params["$filter"] = f"substringof('{safe_search}', EquipmentName)"

    if not cfg["verify_ssl"]:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    response = requests.get(
        url,
        params=params,
        auth=(cfg["username"], cfg["password"]),
        headers={"Accept": "application/json"},
        verify=cfg["verify_ssl"],
        timeout=timeout,
    )

    if not response.ok:
        message = response.text
        try:
            message = response.json()["error"]["message"]["value"]
        except (ValueError, KeyError, TypeError):
            pass
        raise requests.exceptions.HTTPError(
            f"HTTP {response.status_code}: {message}", response=response
        )

    payload = response.json()
    return payload.get("d", {}).get("results", [])
