# ai-generated: 80% - Semgrep rule test cases with ruleid and ok annotations (P-31)
import urllib.request
from fastapi.responses import JSONResponse


def check_urlopen_rule(req):
    # ruleid: svcdesk-dynamic-urlopen
    urllib.request.urlopen(req, timeout=3.0)

    # ok: svcdesk-dynamic-urlopen
    urllib.request.urlopen("https://kb-index.internal/health", timeout=3.0)


def check_exception_response_rule(exc):
    # ruleid: svcdesk-raw-exception-in-jsonresponse
    bad_resp = JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": str(exc)}})

    # ok: svcdesk-raw-exception-in-jsonresponse
    good_resp = JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Invalid input"}})
    return bad_resp, good_resp