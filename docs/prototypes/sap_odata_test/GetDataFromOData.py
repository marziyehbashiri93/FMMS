"""اپلیکیشن Flask برای نمایش داده‌های Equipment از OData سرویس SAP (API_EQUIPMENT)"""

import requests
from flask import Flask, render_template, request

from odata_client import get_equipment

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    top = request.args.get("top", 50, type=int)
    search = request.args.get("search", "").strip()

    error = None
    equipment_list = []
    columns = []

    try:
        equipment_list = get_equipment(top=top, search=search or None)
        if equipment_list:
            columns = [key for key in equipment_list[0].keys() if key != "__metadata"]
    except requests.exceptions.SSLError as exc:
        error = f"خطای گواهی SSL هنگام اتصال به سرور SAP: {exc}"
    except requests.exceptions.ConnectionError as exc:
        error = f"عدم امکان برقراری ارتباط با Application Server: {exc}"
    except requests.exceptions.HTTPError as exc:
        error = f"سرور SAP خطا برگرداند (احتمالا مشکل احراز هویت یا مسیر سرویس): {exc}"
    except FileNotFoundError as exc:
        error = str(exc)
    except ValueError as exc:
        error = str(exc)
    except Exception as exc:  # noqa: BLE001
        error = f"خطای غیرمنتظره: {exc}"

    return render_template(
        "equipment.html",
        equipment_list=equipment_list,
        columns=columns,
        error=error,
        top=top,
        search=search,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
