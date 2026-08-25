POS80_DEVICE_CODE = "pos80"
POS80_VENDOR_IDS = "0483,0416,0fe6,1fc9,04b8"
POS80_REPORT_XMLID = "pba_printer_delivery.action_report_stock_picking_pos80"


def _ensure_pos80_device(env):
    if "device.bridge" not in env:
        return None
    Device = env["device.bridge"]
    device = Device.with_context(active_test=False).search(
        [("code", "=", POS80_DEVICE_CODE)],
        limit=1,
    )
    if device:
        if not device.active:
            device.active = True
    else:
        device = Device.create(
            {
                "name": "POS-80",
                "code": POS80_DEVICE_CODE,
                "device_type": "printer",
                "protocol": "escpos",
                "connection_types": "webusb,websocket",
                "vendor_ids": POS80_VENDOR_IDS,
            }
        )
    report = env.ref(POS80_REPORT_XMLID, raise_if_not_found=False)
    if device and report and "report_ids" in device._fields:
        if report not in device.report_ids:
            device.write({"report_ids": [(4, report.id)]})
    return device


def post_init_hook(env):
    _ensure_pos80_device(env)
