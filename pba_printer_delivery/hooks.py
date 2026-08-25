POS80_DEVICE_CODE = "pos80"
POS80_VENDOR_IDS = "0483,0416,0fe6,1fc9,04b8"


def post_init_hook(env):
    if "device.bridge" not in env:
        return
    Device = env["device.bridge"]
    device = Device.with_context(active_test=False).search(
        [("code", "=", POS80_DEVICE_CODE)],
        limit=1,
    )
    if device:
        if not device.active:
            device.active = True
        return
    Device.create(
        {
            "name": "POS-80",
            "code": POS80_DEVICE_CODE,
            "device_type": "printer",
            "protocol": "escpos",
            "connection_types": "webusb,websocket",
            "vendor_ids": POS80_VENDOR_IDS,
        }
    )
