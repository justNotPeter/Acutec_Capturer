import os
import json
import qrcode

def prompt(msg: str, default: str = "") -> str:
    s = input(f"{msg}{' ['+default+']' if default else ''}: ").strip()
    return s if s else default

def build_payload():
    """
    Keep payload stable for your backend.
    Use this as hinted_object_id and/or meta payload.
    """
    part_id = prompt("ID", "")
    part_type = prompt("Type", "part")
    extra = prompt("Extra JSON (optional, leave blank)", "")

    payload = {
        "part_id": part_id,
        "part_type": part_type,
    }

    if extra:
        try:
            payload["extra"] = json.loads(extra)
        except Exception:
            payload["extra_raw"] = extra

    return payload


def main():
    out_dir = prompt("Output folder", "qr_codes")
    os.makedirs(out_dir, exist_ok=True)

    payload = build_payload()
    if not payload.get("part_id"):
        raise SystemExit("ID is required.")

    # Encode as JSON so CV can parse it consistently
    data_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    img = qrcode.make(data_str)

    fname = f"{payload['part_type']}_{payload['part_id']}.png".replace("/", "_")
    path = os.path.join(out_dir, fname)
    img.save(path)

    print("\n QR created:")
    print("File:", path)
    print("Encoded JSON:", data_str)

if __name__ == "__main__":
    main()