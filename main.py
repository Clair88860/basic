import os
import datetime
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.camera import Camera
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp
from kivy.clock import Clock

from jnius import autoclass, PythonJavaClass, java_method

BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
UUID = autoclass('java.util.UUID')

SERVICE_UUID = UUID.fromString("0000ffe0-0000-1000-8000-00805f9b34fb")
CHAR_UUID = UUID.fromString("0000ffe1-0000-1000-8000-00805f9b34fb")


class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")
        self.nord_value = 0
        self.arduino_connected = False
        self.bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
        self.bluetoothGatt = None

        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        self.build_topbar()
        self.build_camera()
        self.build_capture_button()

        Clock.schedule_once(lambda dt: self.show_camera(), 0.2)

    # =====================================================
    # BLE SCAN
    # =====================================================

    def scan_ble(self):
        if not self.bluetoothAdapter:
            self.status_label.text = "Bluetooth nicht verfügbar"
            return

        devices = self.bluetoothAdapter.getBondedDevices().toArray()

        for device in devices:
            if "Arduino" in device.getName():
                self.status_label.text = "Arduino gefunden"
                self.connect_ble(device)
                return

        self.status_label.text = "Kein Arduino gefunden"

    def connect_ble(self, device):
        self.status_label.text = "Verbinde..."
        self.bluetoothGatt = device.connectGatt(None, False, self)

    # =====================================================
    # GATT CALLBACKS
    # =====================================================

    def onConnectionStateChange(self, gatt, status, newState):
        if newState == 2:  # connected
            self.arduino_connected = True
            gatt.discoverServices()

    def onServicesDiscovered(self, gatt, status):
        service = gatt.getService(SERVICE_UUID)
        if service:
            characteristic = service.getCharacteristic(CHAR_UUID)
            gatt.setCharacteristicNotification(characteristic, True)

    def onCharacteristicChanged(self, gatt, characteristic):
        value = characteristic.getValue().decode("utf-8")
        try:
            self.nord_value = int(value)
            if hasattr(self, "nord_label"):
                self.nord_label.text = f"Norden: {self.nord_value}°"
        except:
            pass

    # =====================================================
    # REST DEINER APP (gekürzt hier für Übersicht)
    # =====================================================

    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1,.08),
                                pos_hint={"top":1})
        for t,f in [("K",self.show_camera),
                    ("G",self.show_gallery),
                    ("E",self.show_settings),
                    ("A",self.show_a),
                    ("H",self.show_help)]:
            b = Button(text=t)
            b.bind(on_press=f)
            self.topbar.add_widget(b)
        self.add_widget(self.topbar)

    def show_a(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False

        if not arduino_on:
            self.add_widget(Label(
                text="Sie müssen die Daten erst in den Einstellungen aktivieren",
                pos_hint={"center_x":.5,"center_y":.5}
            ))
            return

        layout = BoxLayout(orientation="vertical",padding=20,spacing=20)

        self.nord_label = Label(text="Norden: --°",font_size=28)
        layout.add_widget(self.nord_label)

        self.status_label = Label(text="Nicht verbunden")
        layout.add_widget(self.status_label)

        scan_btn = Button(text="Scan nach Arduino")
        scan_btn.bind(on_press=lambda x:self.scan_ble())
        layout.add_widget(scan_btn)

        self.add_widget(layout)

    # Kamera / Galerie Code bleibt wie vorher stabil

class MainApp(App):
    def build(self):
        return Dashboard()

if __name__=="__main__":
    MainApp().run()
