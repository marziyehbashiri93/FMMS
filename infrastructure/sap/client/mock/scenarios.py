"""Canned SAP response payloads for the MockSAPClient.

Each response mirrors the real SAP OData or BAPI response shape so that
adapters can be tested end-to-end without a live SAP connection.

Naming convention:
    ODATA_<SERVICE>_<ENTITY>  — OData GET response wrapper
    BAPI_<FUNCTION_MODULE>    — BAPI export/return dict
"""

from __future__ import annotations

from datetime import UTC, date, datetime

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=UTC).isoformat()
_TODAY = date.today().isoformat()

_SAP_SUCCESS_RETURN: list[dict] = [
    {"TYPE": "S", "ID": "00", "NUMBER": "000", "MESSAGE": "Success", "LOG_NO": ""}
]

_SAP_ERROR_RETURN: list[dict] = [
    {
        "TYPE": "E",
        "ID": "BAPI",
        "NUMBER": "100",
        "MESSAGE": "Error: operation rejected by SAP.",
        "LOG_NO": "",
    }
]

_SAP_DUPLICATE_RETURN: list[dict] = [
    {
        "TYPE": "E",
        "ID": "BAPI",
        "NUMBER": "101",
        "MESSAGE": "Error: document already exists (duplicate key).",
        "LOG_NO": "",
    }
]

# ---------------------------------------------------------------------------
# OData — API_DEFECTCODE_SRV
# ---------------------------------------------------------------------------

ODATA_DEFECT_CODE_SINGLE: dict = {
    "d": {
        "DefectCode": "E0001",
        "DefectCodeText": "Engine oil leak",
        "CatalogProfile": "FLEET",
        "CodeGroup": "ENGINE",
    }
}

ODATA_DEFECT_CODE_LIST: dict = {
    "d": {
        "results": [
            {
                "DefectCode": "E0001",
                "DefectCodeText": "Engine oil leak",
                "CatalogProfile": "FLEET",
                "CodeGroup": "ENGINE",
            },
            {
                "DefectCode": "T0001",
                "DefectCodeText": "Tyre puncture",
                "CatalogProfile": "FLEET",
                "CodeGroup": "TYRES",
            },
            {
                "DefectCode": "B0001",
                "DefectCodeText": "Brake wear",
                "CatalogProfile": "FLEET",
                "CodeGroup": "BRAKES",
            },
        ]
    }
}

# ---------------------------------------------------------------------------
# OData — Object Part Catalog
# ---------------------------------------------------------------------------

ODATA_OBJECT_PART_LIST: dict = {
    "d": {
        "results": [
            {
                "Code": "SEAT",
                "CodeGroup": "SAFETY",
                "CodeText": "Seat belt",
                "CatalogType": "B",
            },
            {
                "Code": "FLIGHT",
                "CodeGroup": "LIGHTS",
                "CodeText": "Front light",
                "CatalogType": "B",
            },
            {
                "Code": "FRIDGE",
                "CodeGroup": "CARGO",
                "CodeText": "Refrigerator",
                "CatalogType": "B",
            },
            {
                "Code": "SAFE",
                "CodeGroup": "SAFETY",
                "CodeText": "Safety equipment",
                "CatalogType": "B",
            },
            {
                "Code": "ENG",
                "CodeGroup": "POWERTRAIN",
                "CodeText": "Engine assembly",
                "CatalogType": "B",
            },
            {
                "Code": "TYR",
                "CodeGroup": "CHASSIS",
                "CodeText": "Tyre and wheel assembly",
                "CatalogType": "B",
            },
        ]
    }
}

ODATA_OBJECT_PART_SINGLE: dict = {
    "d": {
        "Code": "ENG",
        "CodeGroup": "POWERTRAIN",
        "CodeText": "Engine assembly",
        "CatalogType": "B",
    }
}

# ---------------------------------------------------------------------------
# OData — API_PRODUCT_SRV
# ---------------------------------------------------------------------------

ODATA_MATERIAL_SINGLE: dict = {
    "d": {
        "Product": "MAT-001",
        "ProductDesc": "Engine Oil 5W-40 (1L)",
        "BaseUnit": "L",
        "ProductType": "ERSA",
        "Plant": "P001",
        "MaterialGroup": "LUBRICANTS",
    }
}

ODATA_MATERIAL_LIST: dict = {
    "d": {
        "results": [
            {
                "Product": "MAT-001",
                "ProductDesc": "Engine Oil 5W-40 (1L)",
                "BaseUnit": "L",
                "ProductType": "ERSA",
                "Plant": "P001",
                "MaterialGroup": "LUBRICANTS",
            },
            {
                "Product": "MAT-002",
                "ProductDesc": "Air Filter — Fleet Standard",
                "BaseUnit": "EA",
                "ProductType": "ERSA",
                "Plant": "P001",
                "MaterialGroup": "FILTERS",
            },
        ]
    }
}

# ---------------------------------------------------------------------------
# OData — API_MATERIAL_STOCK_SRV
# ---------------------------------------------------------------------------

ODATA_STOCK_SINGLE: dict = {
    "d": {
        "Material": "MAT-001",
        "Plant": "P001",
        "StorageLocation": "SL01",
        "MatlStkQtyInMatlBaseUnit": "50.000",
        "MaterialBaseUnit": "L",
    }
}

ODATA_STOCK_LIST: dict = {
    "d": {
        "results": [
            {
                "Material": "MAT-001",
                "Plant": "P001",
                "StorageLocation": "SL01",
                "MatlStkQtyInMatlBaseUnit": "50.000",
                "MaterialBaseUnit": "L",
            },
            {
                "Material": "MAT-002",
                "Plant": "P001",
                "StorageLocation": "SL01",
                "MatlStkQtyInMatlBaseUnit": "120.000",
                "MaterialBaseUnit": "EA",
            },
        ]
    }
}

# ---------------------------------------------------------------------------
# BAPI — PM Notification
# ---------------------------------------------------------------------------

BAPI_PM_NOTIFICATION_CREATE_SUCCESS: dict = {
    "NOTIFNO": "10000099",
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_PM_NOTIFICATION_CLOSE_SUCCESS: dict = {
    "NOTIFNO": "10000099",
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_PM_NOTIFICATION_ERROR: dict = {
    "NOTIFNO": "",
    "RETURN": _SAP_ERROR_RETURN,
}

BAPI_PM_NOTIFICATION_DUPLICATE: dict = {
    "NOTIFNO": "",
    "RETURN": _SAP_DUPLICATE_RETURN,
}

# ---------------------------------------------------------------------------
# BAPI — PM Order
# ---------------------------------------------------------------------------

BAPI_PM_ORDER_CREATE_SUCCESS: dict = {
    "ORDER_NUMBER": "20000001",
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_PM_ORDER_COMPLETE_SUCCESS: dict = {
    "ORDER_NUMBER": "20000001",
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_PM_ORDER_GET_SUCCESS: dict = {
    "ORDER_HEADER_DATA": {
        "ORDERID": "20000001",
        "EQUNR": "10000001",
        "AUART": "PM01",
        "SYSST": "REL",
        "GSTRP": _TODAY,
        "GLTRP": _TODAY,
        "QMNUM": "",
    },
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_PM_ORDER_ERROR: dict = {
    "ORDER_NUMBER": "",
    "RETURN": _SAP_ERROR_RETURN,
}

# ---------------------------------------------------------------------------
# BAPI — Purchase Requisition
# ---------------------------------------------------------------------------

BAPI_PR_CREATE_SUCCESS: dict = {
    "NUMBER": "10000200",
    "PRITEM": [
        {
            "PREQ_ITEM": "00010",
            "MATERIAL": "MAT-001",
            "QUANTITY": "10.000",
            "UNIT": "L",
        }
    ],
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_PR_CREATE_ERROR: dict = {
    "NUMBER": "",
    "PRITEM": [],
    "RETURN": _SAP_ERROR_RETURN,
}

BAPI_PR_CREATE_DUPLICATE: dict = {
    "NUMBER": "",
    "PRITEM": [],
    "RETURN": _SAP_DUPLICATE_RETURN,
}

BAPI_PR_GET_SUCCESS: dict = {
    "NUMBER": "10000200",
    "PRITEM": [
        {
            "PREQ_ITEM": "00010",
            "MATERIAL": "MAT-001",
            "QUANTITY": "10.000",
            "UNIT": "L",
        }
    ],
    "RETURN": _SAP_SUCCESS_RETURN,
}

# ---------------------------------------------------------------------------
# BAPI — Purchase Order
# ---------------------------------------------------------------------------

BAPI_PO_CREATE_SUCCESS: dict = {
    "PURCHASEORDER": "45000100",
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_PO_CREATE_ERROR: dict = {
    "PURCHASEORDER": "",
    "RETURN": _SAP_ERROR_RETURN,
}

BAPI_PO_APPROVE_SUCCESS: dict = {
    "PURCHASEORDER": "45000100",
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_PO_GET_SUCCESS: dict = {
    "PO_HEADER": {
        "PO_NUMBER": "45000100",
        "VENDOR": "V-001",
        "DOC_TYPE": "NB",
        "PMNTTRMS": "",
    },
    "RETURN": _SAP_SUCCESS_RETURN,
}

# ---------------------------------------------------------------------------
# BAPI — Goods Receipt
# ---------------------------------------------------------------------------

BAPI_GR_POST_SUCCESS: dict = {
    "MATERIALDOCUMENT": "5000012345",
    "MATDOCUMENTYEAR": "2026",
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_GR_POST_ERROR: dict = {
    "MATERIALDOCUMENT": "",
    "MATDOCUMENTYEAR": "",
    "RETURN": _SAP_ERROR_RETURN,
}

BAPI_GR_REVERSE_SUCCESS: dict = {
    "MATERIALDOCUMENT": "5000012346",
    "MATDOCUMENTYEAR": "2026",
    "RETURN": _SAP_SUCCESS_RETURN,
}

# ---------------------------------------------------------------------------
# BAPI — Goods Issue
# ---------------------------------------------------------------------------

BAPI_GI_POST_SUCCESS: dict = {
    "MATERIALDOCUMENT": "4900012345",
    "MATDOCUMENTYEAR": "2026",
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_GI_POST_ERROR: dict = {
    "MATERIALDOCUMENT": "",
    "MATDOCUMENTYEAR": "",
    "RETURN": _SAP_ERROR_RETURN,
}

BAPI_GI_REVERSE_SUCCESS: dict = {
    "MATERIALDOCUMENT": "4900012346",
    "MATDOCUMENTYEAR": "2026",
    "RETURN": _SAP_SUCCESS_RETURN,
}

# ---------------------------------------------------------------------------
# BAPI — Service PO
# ---------------------------------------------------------------------------

BAPI_SERVICE_PO_CREATE_SUCCESS: dict = {
    "PURCHASEORDER": "45000200",
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_SERVICE_PO_CREATE_ERROR: dict = {
    "PURCHASEORDER": "",
    "RETURN": _SAP_ERROR_RETURN,
}

BAPI_SERVICE_PO_CONFIRM_SUCCESS: dict = {
    "PURCHASEORDER": "45000200",
    "RETURN": _SAP_SUCCESS_RETURN,
}

BAPI_SERVICE_PO_GET_SUCCESS: dict = {
    "PO_HEADER": {
        "PO_NUMBER": "45000200",
        "VENDOR": "V-002",
        "DOC_TYPE": "FWRK",
    },
    "RETURN": _SAP_SUCCESS_RETURN,
}
