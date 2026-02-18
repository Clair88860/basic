from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
import struct

# Android-spezifische Importe
if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothDevice = autoclass("android.bluetooth.BluetoothDevice")
    BluetoothGattDescriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
    UUID = autoclass("java.util.UUID")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity
else:
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

class BLEScanCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothAdapter$LeScanCallback"]
    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/bluetooth/BluetoothDevice;I[B)V")
    def onLeScan(self, device, rssi, scanRecord):
        name = device.getName()
        if name == "Arduino_GCS":
            self.app.log(f"Gefunden: {name}")
            self.app.connect(device)

class GattCallback(PythonJavaClass):
    __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]
    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/bluetooth/BluetoothGatt;II)V")
    def onConnectionStateChange(self, gatt, status, newState):
        if newState == 2:  # STATE_CONNECTED
            self.app.log("Verbunden! Suche Services...")
            Clock.schedule_once(lambda dt: gatt.discoverServices(), 1.0)
        elif newState == 0:  # STATE_DISCONNECTED
            self.app.log("Verbindung getrennt.")

    @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
    def onServicesDiscovered(self, gatt, status):
        self.app.log("Services entdeckt")
        services = gatt.getServices()
        for i in range(services.size()):
            s = services.get(i)
            chars = s.getCharacteristics()
            for j in range(chars.size()):
                c = chars.get(j)
                # Beispiel: Aktiviere Benachrichtigungen auf der ersten Characteristic
                gatt.setCharacteristicNotification(c, True)
                d = c.getDescriptor(UUID.fromString(CCCD_UUID))
                if d:
                    d.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
                    gatt.writeDescriptor(d)

    @java_method("(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V")
    def onCharacteristicChanged(self, gatt, characteristic):
        data = characteristic.getValue()
        if data:
            try:
                angle = struct.unpack('<h', bytes(data))[0]
                Clock.schedule_once(lambda dt: self.app.update_data(angle))
            except Exception as e:
                self.app.log(f"Fehler: {str(e)}")

class BLEApp(App):
    def build(self):
        self.root = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.angle_lbl = Label(text="0°", font_size=100, size_hint_y=0.4)
        self.status_btn = Button(text="Scan starten", size_hint_y=0.2, on_press=self.start_scan)
        self.scroll = ScrollView(size_hint_y=0.4)
        self.log_lbl = Label(text="Bereit\n", size_hint_y=None, halign="left", valign="top")
        self.log_lbl.bind(texture_size=self.log_lbl.setter('size'))
        self.scroll.add_widget(self.log_lbl)
        self.root.add_widget(self.angle_lbl)
        self.root.add_widget(self.status_btn)
        self.root.add_widget(self.scroll)

        self.gatt = None
        self.scan_cb = None
        self.gatt_cb = None
        return self.root

    def log(self, txt):
        Clock.schedule_once(lambda dt: setattr(self.log_lbl, 'text', self.log_lbl.text + txt + "\n"))

    def on_start(self):
        if platform == "android":
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.BLUETOOTH_SCAN,
                Permission.BLUETOOTH_CONNECT
            ], self.check_permissions)

    def check_permissions(self, permissions, results):
        if all(results):
            self.log("Alle Berechtigungen erteilt.")
        else:
            self.log("Berechtigungen fehlen!")

    def start_scan(self, *args):
        if platform != "android":
            self.log("Nur auf Android verfügbar!")
            return
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                self.log("Bitte Bluetooth aktivieren!")
                return
            self.log("Scanne nach BLE-Geräten...")
            self.status_btn.text = "Suche..."
            self.scan_cb = BLEScanCallback(self)
            adapter.startLeScan(self.scan_cb)
        except Exception as e:
            self.log(f"Scan Fehler: {str(e)}")

    def connect(self, device):
        adapter = BluetoothAdapter.getDefaultAdapter()
        adapter.stopLeScan(self.scan_cb)
        self.log(f"Verbinde mit {device.getAddress()}...")
        self.gatt_cb = GattCallback(self)
        self.gatt = device.connectGatt(mActivity, False, self.gatt_cb, 2)

    def update_data(self, angle):
        self.angle_lbl.text = f"{angle}°"
        self.status_btn.text = "Daten empfangen"

    def on_stop(self):
        if self.gatt:
            self.gatt.close()

if __name__ == "__main__":
    BLEApp().run()
