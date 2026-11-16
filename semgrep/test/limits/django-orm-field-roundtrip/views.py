from models import Device


def list_health():
    for device in Device.objects.filter(is_active=True):
        print(device.status)
