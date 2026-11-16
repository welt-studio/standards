from models import Device


def check(device: Device):
    try:
        ping()
    except Exception as e:
        device.status = {"error": str(e)}
        device.save()
        print(device.status)


def ping():
    pass
