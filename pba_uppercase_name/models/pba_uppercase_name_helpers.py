def pba_uppercase_name_value(value):
    if isinstance(value, str):
        return value.upper()
    if isinstance(value, dict):
        return {
            key: (item.upper() if isinstance(item, str) else item)
            for key, item in value.items()
        }
    return value


def pba_uppercase_name_in_vals(record, vals):
    if not vals:
        return
    name_field = record._fields.get("name")
    if name_field and name_field.type in ("char", "text") and "name" in vals:
        vals["name"] = pba_uppercase_name_value(vals["name"])


def pba_uppercase_name_in_vals_list(record, vals_list):
    for vals in vals_list:
        pba_uppercase_name_in_vals(record, vals)
