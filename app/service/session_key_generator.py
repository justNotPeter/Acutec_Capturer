def generate_inspection_key(part_id: str, first_image_utc: str) -> str:
    part_id = str(part_id).strip()
    first_image_utc = str(first_image_utc).strip()

    if not part_id:
        raise ValueError("part_id is required")

    if not first_image_utc:
        raise ValueError("first_image_utc is required")

    normalized_ts = (
        first_image_utc
        .replace("-", "")
        .replace(":", "")
        .replace("+00:00", "Z")
    )

    return f"{part_id}_{normalized_ts}"
