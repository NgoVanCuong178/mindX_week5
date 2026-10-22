"""Kiểm chứng các thao tác GHI lên Odoo qua External JSON-2 API (Giai đoạn 4 - Bước 0).

Mục đích: biết chắc tham số đúng của message_post (ghi chú / email), write (thẻ, giai đoạn)
trên Odoo 20 trước khi viết adapter - theo nguyên tắc "verify, không đoán".

An toàn:
  - Chỉ thao tác trên ticket có tiêu đề bắt đầu bằng "[TEST]".
  - Mặc định CHỈ ĐỌC. Thêm --apply mới ghi (ghi chú, email, thẻ, giai đoạn).

Chạy:
  python scripts/spike_odoo_write.py            # chỉ đọc: tìm ticket test, thẻ, giai đoạn
  python scripts/spike_odoo_write.py --apply    # ghi thử lên ticket test
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
TEST_PREFIX = "[TEST]"
REQUIRED_TAGS = ["auto-processed", "auto-reactivated", "auto-password-guide",
                 "needs-review", "automation-failed", "possible-incident"]


def load_env() -> dict:
    if not ENV_PATH.exists():
        sys.exit(f"[LỖI] Không thấy {ENV_PATH}")
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def call(env: dict, model: str, method: str, payload: dict):
    """Gọi POST /json/2/<model>/<method>; in lỗi HTTP rõ ràng rồi dừng."""
    headers = {"Content-Type": "application/json", "Authorization": f"bearer {env['ODOO_API_KEY']}"}
    if env.get("ODOO_DB"):
        headers["X-Odoo-Database"] = env["ODOO_DB"]
    request = urllib.request.Request(f"{env['ODOO_URL']}/json/2/{model}/{method}",
                                     data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        print(f"[LỖI] {model}.{method} -> HTTP {exc.code}: {body}")
        return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="ghi thử lên ticket test")
    args = parser.parse_args()
    env = load_env()

    print("== 1. Tìm ticket test ==")
    tickets = call(env, "helpdesk.ticket", "search_read", {
        "domain": [["name", "=like", f"{TEST_PREFIX}%"]],
        "fields": ["id", "name", "partner_id", "partner_email", "stage_id", "tag_ids", "team_id"],
        "limit": 5,
    }) or []
    if not tickets:
        sys.exit(f"[DỪNG] Chưa có ticket nào có tiêu đề bắt đầu bằng '{TEST_PREFIX}'. Tạo ticket test trên Odoo trước.")
    ticket = tickets[0]
    print(f"[OK] Ticket id={ticket['id']} | {ticket['name']} | giai đoạn={ticket['stage_id']} | "
          f"khách hàng có email: {'có' if ticket.get('partner_email') else 'KHÔNG'}")

    print("\n== 2. Thẻ cần cho workflow ==")
    tags = call(env, "helpdesk.tag", "search_read",
                {"domain": [["name", "in", REQUIRED_TAGS]], "fields": ["id", "name"]}) or []
    found = {t["name"]: t["id"] for t in tags}
    for name in REQUIRED_TAGS:
        print(f"  - {name:<22} {'id=' + str(found[name]) if name in found else 'CHƯA TẠO'}")

    print("\n== 3. Giai đoạn của đội ==")
    team_id = ticket["team_id"][0] if ticket.get("team_id") else None
    stages = call(env, "helpdesk.stage", "search_read", {
        "domain": [["team_ids", "in", [team_id]]] if team_id else [],
        "fields": ["id", "name", "sequence"], "order": "sequence",
    }) or []
    for stage in stages:
        print(f"  - id={stage['id']:<4} {stage['name']}")

    if not args.apply:
        print("\n[CHỈ ĐỌC] Thêm --apply để ghi thử ghi chú, email, thẻ và giai đoạn lên ticket test.")
        return
    if not ticket["name"].startswith(TEST_PREFIX):
        sys.exit("[DỪNG] Ticket không phải ticket test.")

    print("\n== 4. Ghi thử (chỉ trên ticket test) ==")
    note = call(env, "helpdesk.ticket", "message_post", {
        "ids": [ticket["id"]],
        "body": "[SPIKE] Ghi chú nội bộ thử từ JSON-2 API.\nDòng thứ hai để kiểm tra xuống dòng.",
        "message_type": "comment", "subtype_xmlid": "mail.mt_note",
    })
    print(f"  - Ghi chú nội bộ (mail.mt_note): {'OK, message id=' + str(note) if note else 'THẤT BẠI'}")

    partner_ids = [ticket["partner_id"][0]] if ticket.get("partner_id") else []
    email = call(env, "helpdesk.ticket", "message_post", {
        "ids": [ticket["id"]],
        "body": "Chào anh/chị,\n\nĐây là email thử từ JSON-2 API.\n\nTrân trọng,\nMindX Tech Support",
        "message_type": "comment", "subtype_xmlid": "mail.mt_comment", "partner_ids": partner_ids,
    })
    print(f"  - Email cho khách (mail.mt_comment): {'OK, message id=' + str(email) if email else 'THẤT BẠI'}")

    if "auto-processed" in found:
        ok = call(env, "helpdesk.ticket", "write",
                  {"ids": [ticket["id"]], "vals": {"tag_ids": [[4, found["auto-processed"]]]}})
        print(f"  - Gắn thẻ auto-processed ([4, id]): {'OK' if ok else 'THẤT BẠI'}")

    in_progress = next((s for s in stages if s["name"] in ("Đang thực hiện", "In Progress")), None)
    if in_progress:
        ok = call(env, "helpdesk.ticket", "write", {"ids": [ticket["id"]], "vals": {"stage_id": in_progress["id"]}})
        print(f"  - Chuyển giai đoạn sang '{in_progress['name']}': {'OK' if ok else 'THẤT BẠI'}")

    print("\nMở ticket test trên Odoo và kiểm tra chatter: ghi chú, email (xuống dòng có đúng không), thẻ, giai đoạn.")


if __name__ == "__main__":
    main()
