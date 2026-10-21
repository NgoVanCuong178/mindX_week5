"""Kiểm tra kết nối tới Odoo bằng API key (Giai đoạn 0).

Thử lần lượt:
  1. External JSON-2 API (Odoo 19+): POST /json/2/<model>/<method>, header "Authorization: bearer <key>"
  2. XML-RPC cũ (/xmlrpc/2): cần ODOO_DB + ODOO_USERNAME

Chạy:  python scripts/check_odoo_connection.py
Đọc cấu hình từ file .env ở thư mục gốc repo. Không in API key ra màn hình.
"""
import json
import sys
import urllib.error
import urllib.request
import xmlrpc.client
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
TICKET_FIELDS = ["create_date", "close_date", "close_hours", "first_response_hours", "tag_ids", "stage_id"]


def load_env(path: Path) -> dict:
    """Đọc file .env dạng KEY=VALUE, bỏ qua dòng trống và comment."""
    if not path.exists():
        sys.exit(f"[LỖI] Không thấy {path}. Copy .env.example thành .env rồi điền giá trị.")
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    for key in ("ODOO_URL", "ODOO_API_KEY"):
        if not env.get(key):
            sys.exit(f"[LỖI] Thiếu {key} trong .env")
    return env


def json2_call(env: dict, model: str, method: str, payload: dict):
    """Gọi External JSON-2 API của Odoo; trả về kết quả đã parse JSON."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"bearer {env['ODOO_API_KEY']}",
    }
    if env.get("ODOO_DB"):
        headers["X-Odoo-Database"] = env["ODOO_DB"]
    request = urllib.request.Request(
        f"{env['ODOO_URL']}/json/2/{model}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def try_json2(env: dict) -> bool:
    print("\n== Cách 1: External JSON-2 API ==")
    try:
        user = json2_call(env, "res.users", "context_get", {})
        print(f"[OK] Xác thực bằng API key thành công (ngôn ngữ: {user.get('lang')})")
        count = json2_call(env, "helpdesk.ticket", "search_count", {"domain": []})
        print(f"[OK] Đọc được helpdesk.ticket: {count} ticket")
        fields = json2_call(env, "helpdesk.ticket", "fields_get",
                            {"allfields": TICKET_FIELDS, "attributes": ["string"]})
        for name in TICKET_FIELDS:
            print(f"  - {name:<22} {'có' if name in fields else 'KHÔNG có'}")
        return True
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        print(f"[LỖI] HTTP {exc.code}: {body}")
    except (urllib.error.URLError, OSError) as exc:
        print(f"[LỖI] Không kết nối được: {exc}")
    return False


def try_xmlrpc(env: dict) -> bool:
    print("\n== Cách 2: XML-RPC (cũ) ==")
    if not (env.get("ODOO_DB") and env.get("ODOO_USERNAME")):
        print("[BỎ QUA] Cần ODOO_DB và ODOO_USERNAME trong .env")
        return False
    try:
        common = xmlrpc.client.ServerProxy(f"{env['ODOO_URL']}/xmlrpc/2/common")
        print(f"Odoo server: {common.version().get('server_version')}")
        uid = common.authenticate(env["ODOO_DB"], env["ODOO_USERNAME"], env["ODOO_API_KEY"], {})
        if not uid:
            print("[LỖI] Đăng nhập thất bại (sai DB / username / key, hoặc key không dùng được cho XML-RPC)")
            return False
        print(f"[OK] Đăng nhập thành công, uid = {uid}")
        return True
    except xmlrpc.client.Fault as exc:
        print(f"[LỖI] Odoo từ chối: {exc.faultString[:300]}")
    except OSError as exc:
        print(f"[LỖI] Không kết nối được: {exc}")
    return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    env = load_env(ENV_PATH)
    ok_json2 = try_json2(env)
    ok_xmlrpc = try_xmlrpc(env)
    print("\n== Kết luận ==")
    if ok_json2:
        print("Dùng External JSON-2 API cho workflow.")
    elif ok_xmlrpc:
        print("Dùng XML-RPC cho workflow.")
    else:
        print("Chưa kết nối được. Gửi toàn bộ kết quả ở trên để kiểm tra (không chứa API key).")


if __name__ == "__main__":
    main()
