from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
import struct
import math

# Android Imports
if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothGattDescriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
    UUID = autoclass("java.util.UUID")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity

    SensorManager = autoclass("android.hardware.SensorManager")
    Sensor = autoclass("android.hardware.Sensor")
    Context = autoclass("android.content.Context")
else:
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

# ---------------- Richtungsberechnung ----------------
def angle_to_direction(angle):
    angle = angle % 360
    if angle >= 337.5 or angle < 22.5:
        return "Nord"
    elif angle < 67.5:
        return "Nordost"
    elif angle < 112.5:
        return "Ost"
    elif angle < 157.5:
        return "Südost"
    elif angle < 202.5:
        return "Süd"
    elif angle < 247.5:
        return "Südwest"
    elif angle < 292.5:
        return "West"
    else:
        return "Nordwest"

# ---------------- BLE Callback ----------------
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
        elif newState == 0:
            self.app.log("Verbindung getrennt.")

    @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
    def onServicesDiscovered(self, gatt, status):
        self.app.log("Services entdeckt")
        services = gatt.getServices()
        for i in range(services.size()):
            s = services.get(i)
            s_uuid = s.getUuid().toString().lower()
            if "180a" in s_uuid:
                chars = s.getCharacteristics()
                for j in range(chars.size()):
                    c = chars.get(j)
                    if "2a57" in c.getUuid().toString().lower():
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
                self.app.update_ble_direction(angle)
            except Exception as e:
                self.app.log(f"Fehler: {str(e)}")

# ---------------- Main App ----------------
class BLEApp(App):
    def build(self):
        self.root = BoxLayout(orientation='vertical', padding=20, spacing=10)

        self.direction_lbl = Label(text="Richtung: Nord", font_size=80, size_hint_y=0.4)
        self.angle_lbl = Label(text="0°", font_size=60, size_hint_y=0.2)

        self.status_btn = Button(text="Scan starten", size_hint_y=0.2, on_press=self.start_scan)
        self.scroll = ScrollView(size_hint_y=0.2)
        self.log_lbl = Label(text="Bereit\n", size_hint_y=None, halign="left", valign="top")
        self.log_lbl.bind(texture_size=self.log_lbl.setter('size'))
        self.scroll.add_widget(self.log_lbl)

        self.root.add_widget(self.direction_lbl)
        self.root.add_widget(self.angle_lbl)
        self.root.add_widget(self.status_btn)
        self.root.add_widget(self.scroll)

        self.gatt = None
        self.scan_cb = None
        self.gatt_cb = None
        self.ble_angle = None

        # Fallback: Smartphone Kompass
        if platform == "android":
            Clock.schedule_interval(self.update_fallback_direction, 1.0)

            # SensorManager Setup
            self.sensor_manager = mActivity.getSystemService(Context.SENSOR_SERVICE)
            self.rotation_sensor = self.sensor_manager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)
            self.orientation = 0.0
            self.sensor_listener = self.create_sensor_listener()
            self.sensor_manager.registerListener(
                self.sensor_listener,
                self.rotation_sensor,
                SensorManager.SENSOR_DELAY_UI
            )

        return self.root

    # ---------------- BLE ----------------
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
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                self.log("Bitte Bluetooth aktivieren!")
                return
            self.log("Scanne...")
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

    def update_ble_direction(self, angle):
        dir_str = angle_to_direction(angle)
        Clock.schedule_once(lambda dt: setattr(self.direction_lbl, 'text', f"Richtung: {dir_str}"))
        Clock.schedule_once(lambda dt: setattr(self.angle_lbl, 'text', f"{angle}°"))
        self.ble_angle = angle

    # ---------------- Fallback Kompass ----------------
    def create_sensor_listener(self):
        class Listener(PythonJavaClass):
            __javainterfaces__ = ["android/hardware/SensorEventListener"]

            def __init__(self, app):
                super().__init__()
                self.app = app

            @java_method("(Landroid/hardware/SensorEvent;)V")
            def onSensorChanged(self, event):
                # Rotation Vector -> Azimut
                rotation = event.values
                if len(rotation) >= 3:
                    R = [0]*9
                    SensorManager.getRotationMatrixFromVector(R, rotation)
                    orientation = SensorManager.getOrientation(R, [0.0, 0.0, 0.0])
                    azimut = math.degrees(orientation[0])
                    if azimut < 0:
                        azimut += 360
                    self.app.orientation = azimut

            @java_method("(Landroid/hardware/Sensor;I)V")
            def onAccuracyChanged(self, sensor, accuracy):
                pass

        return Listener(self)

    def update_fallback_direction(self, dt):
        if self.ble_angle is None:
            dir_str = angle_to_direction(self.orientation)
            self.direction_lbl.text = f"Richtung: {dir_str}"
            self.angle_lbl.text = f"{int(self.orientation)}°"

    def on_stop(self):
        if self.gatt:
            self.gatt.close()
        if platform == "android" and hasattr(self, 'sensor_manager'):
            self.sensor_manager.unregisterListener(self.sensor_listener)


if __name__ == "__main__":
    BLEApp().run()
