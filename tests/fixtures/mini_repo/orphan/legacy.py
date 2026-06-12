"""Dead code from an abandoned migration — no inbound edges anywhere."""


def convert_v1_record(record):
    return {"name": record.get("title", ""), "value": float(record.get("amount", 0))}
