from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
import struct

# ---------------- UUIDs ----------------
SERVICE_UUID = "12345678-1234-1234-1234-1234567890ab"
CHAR_UUID    = "12345678-1234-1234-1234-1234567890ac"
CCCD_UUID    = "00002902-0000-1000-8000-00805f9b34fb"

# ---------------- Android Imports ----------------
if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothLeScanner = autoclass("android.bluetooth.le.BluetoothLeScanner")
    BluetoothGattDescriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
    UUID = autoclass("java.util.UUID")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity
else:
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x


# =====================================================
# ===================== APP ===========================
# =====================================================

class BLEApp(App):

    def build(self):
        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        self.angle_label = Label(text="0.0°", font_size=80)
        self.button = Button(text="Scan starten", size_hint_y=0.2)
        self.button.bind(on_press=self.start_scan)

        self.log_label = Label(text="Bereit\n", size_hint_y=None)
        self.log_label.bind(texture_size=self.log_label.setter("size"))

        scroll = ScrollView()
        scroll.add_widget(self.log_label)

        layout.add_widget(self.angle_label)
        layout.add_widget(self.button)
        layout.add_widget(scroll)

        # BLE Referenzen
        self.gatt = None
        self.scan_callback = None
        self.gatt_callback = None
        self.scanner = None

        return layout

    # -------------------------------------------------
    def log(self, msg):
        Clock.schedule_once(lambda dt:
            setattr(self.log_label, "text", self.log_label.text + msg + "\n"))

    # -------------------------------------------------
    def on_start(self):
        if platform == "android":
            from android.permissions import request_permissions, Permission

            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.BLUETOOTH_SCAN,
                Permission.BLUETOOTH_CONNECT
            ])

    # -------------------------------------------------
    def start_scan(self, *args):
        if platform != "android":
            self.log("Nur Android unterstützt")
            return

        adapter = BluetoothAdapter.getDefaultAdapter()
        if not adapter or not adapter.isEnabled():
            self.log("Bluetooth nicht aktiviert!")
            return

        self.log("Scanne...")
        self.button.text = "Suche..."

        self.scanner = adapter.getBluetoothLeScanner()
        self.scan_callback = self.ScanCallback(self)
        self.scanner.startScan(self.scan_callback)

    # =====================================================
    # =================== SCAN CALLBACK ===================
    # =====================================================

    class ScanCallback(PythonJavaClass):
        __javainterfaces__ = ["android/bluetooth/le/ScanCallback"]

        def __init__(self, app):
            super().__init__()
            self.app = app

        @java_method("(ILandroid/bluetooth/le/ScanResult;)V")
        def onScanResult(self, callbackType, result):
            device = result.getDevice()
            name = device.getName()

            if name and "Arduino_GCS" in name:
                self.app.log(f"Arduino gefunden: {name}")
                # Scanner stoppen
                if self.app.scanner:
                    self.app.scanner.stopScan(self)
                self.app.connect(device)

    # -------------------------------------------------
    def connect(self, device):
        self.log("Verbinde...")
        self.gatt_callback = self.GattCallback(self)
        self.gatt = device.connectGatt(
            mActivity,
            False,
            self.gatt_callback,
            2  # TRANSPORT_LE
        )

    # =====================================================
    # =================== GATT CALLBACK ===================
    # =====================================================

    class GattCallback(PythonJavaClass):
        __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]

        def __init__(self, app):
            super().__init__()
            self.app = app

        @java_method("(Landroid/bluetooth/BluetoothGatt;II)V")
        def onConnectionStateChange(self, gatt, status, newState):
            if newState == 2:  # STATE_CONNECTED
                self.app.log("Verbunden!")
                gatt.discoverServices()
            elif newState == 0:  # STATE_DISCONNECTED
                self.app.log("Getrennt")

        @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
        def onServicesDiscovered(self, gatt, status):
            services = gatt.getServices()
            for i in range(services.size()):
                s = services.get(i)
                self.app.log("Service: " + s.getUuid().toString())

            service = gatt.getService(UUID.fromString(SERVICE_UUID))
            if not service:
                self.app.log("Service nicht gefunden!")
                return

            characteristic = service.getCharacteristic(UUID.fromString(CHAR_UUID))
            if not characteristic:
                self.app.log("Characteristic nicht gefunden!")
                return

            gatt.setCharacteristicNotification(characteristic, True)
            descriptor = characteristic.getDescriptor(UUID.fromString(CCCD_UUID))
            descriptor.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
            gatt.writeDescriptor(descriptor)

            self.app.log("Notifications aktiviert!")

        @java_method("(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V")
        def onCharacteristicChanged(self, gatt, characteristic):
            data = characteristic.getValue()
            if not data:
                return
            try:
                value = struct.unpack('<f', bytes(data))[0]
                Clock.schedule_once(lambda dt:
                    setattr(self.app.angle_label, "text", f"{value:.1f}°"))
            except Exception as e:
                self.app.log("Fehler: " + str(e))

    # -------------------------------------------------
    def on_stop(self):
        if self.gatt:
            self.gatt.close()


# =====================================================
if __name__ == "__main__":
    BLEApp().run()
