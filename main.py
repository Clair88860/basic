import asyncio
from bleak import BleakClient, BleakScanner
import struct

SERVICE_UUID = "180A"
CHARACTERISTIC_UUID = "2A57"

async def read_arduino_ble():
    print("Scanne nach BLE-Geräten...")
    devices = await BleakScanner.discover()
    
    arduino_device = None
    for d in devices:
        if "Arduino_GCS" in d.name:
            arduino_device = d
            break

    if not arduino_device:
        print("Arduino nicht gefunden!")
        return

    print(f"Verbinde zu {arduino_device.name} ({arduino_device.address}) ...")

    async with BleakClient(arduino_device.address) as client:
        if not client.is_connected:
            print("Verbindung fehlgeschlagen")
            return
        print("Verbunden!")

        def handle_notification(sender, data):
            winkel = struct.unpack('<f', data)[0]
            print(f"Winkel: {winkel:.1f}°")

        await client.start_notify(CHARACTERISTIC_UUID, handle_notification)

        print("Daten werden empfangen. Strg+C zum Beenden.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Beende Verbindung...")
            await client.stop_notify(CHARACTERISTIC_UUID)

asyncio.run(read_arduino_ble())
