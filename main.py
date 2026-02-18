from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.clock import Clock
from kivy.utils import platform
import struct

# Dummy-Winkel, falls kein Arduino
dummy_angle = 0.0

# Funktion, um Winkel in Richtung umzuwandeln
def direction_from_angle(angle):
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

# -------------------- APP --------------------
class BLEFallbackApp(App):
    def build(self):
        self.root = BoxLayout(orientation='vertical', padding=20, spacing=10)

        # Labels
        self.angle_label = Label(text="Winkel: 0°", font_size=50)
        self.direction_label = Label(text="Richtung: Nord", font_size=50)

        # Slider für manuellen Dummy-Winkel
        self.slider = Slider(min=0, max=360, value=0)
        self.slider.bind(value=self.on_slider_change)

        # Button: Simuliert BLE Scan/Verbindung (nur Dummy)
        self.button = Button(text="Scan starten (Dummy BLE)", size_hint_y=0.2)
        self.button.bind(on_press=self.on_scan_dummy)

        # Hinzufügen
        self.root.add_widget(self.angle_label)
        self.root.add_widget(self.direction_label)
        self.root.add_widget(self.slider)
        self.root.add_widget(self.button)

        # BLE Platzhalter
        self.ble_connected = False
        self.ble_angle = None  # Wenn Arduino Daten sendet

        # Timer für Dummy-Werte
        Clock.schedule_interval(self.update_display, 0.2)

        return self.root

    # ----------------- Slider Callback -----------------
    def on_slider_change(self, instance, value):
        global dummy_angle
        dummy_angle = value

    # ----------------- Dummy Scan -----------------
    def on_scan_dummy(self, instance):
        self.ble_connected = True
        self.ble_angle = None  # Anfang: kein Wert vom Arduino
        self.log("BLE Scan gestartet (Dummy)")

    def log(self, msg):
        print(msg)

    # ----------------- Display Update -----------------
    def update_display(self, dt):
        # Wenn BLE-Wert da, benutze ihn, sonst Dummy
        angle = self.ble_angle if self.ble_angle is not None else dummy_angle

        self.angle_label.text = f"Winkel: {angle:.1f}°"
        self.direction_label.text = f"Richtung: {direction_from_angle(angle)}"

    # ----------------- BLE Dummy Funktion -----------------
    def receive_ble_data(self, angle_value):
        """Simuliert den Eingang von Arduino-Daten"""
        self.ble_angle = angle_value


if __name__ == "__main__":
    BLEFallbackApp().run()
