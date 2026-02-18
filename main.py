import os
import math
import datetime
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp
from kivy.clock import Clock

try:
    from android.permissions import check_permission, Permission
except:
    check_permission = None
    Permission = None

from kivy.utils import platform

# ---------------- Dashboard ----------------
class Dashboard(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.store = JsonStore("settings.json")
        self.orientation_angle = 0

        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        # Dashboard oben
        self.build_topbar()
        self.build_camera()
        self.build_capture_button()

        Clock.schedule_once(lambda dt: self.show_camera(), 0.2)
        Clock.schedule_interval(self.update_a_page, 0.5)

    # ---------------- Topbar ----------------
    def build_topbar(self):
        self.topbar = BoxLayout(
            size_hint=(1, .08),
            spacing=5,
            padding=5,
            pos_hint={"top": 1}
        )
        for t, f in [
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings),
            ("A", self.show_a),
            ("H", self.show_help)
        ]:
            b = Button(text=t, background_normal="", background_color=(0.15,0.15,0.15,1), color=(1,1,1,1))
            b.bind(on_press=f)
            self.topbar.add_widget(b)
        self.add_widget(self.topbar)

    # ---------------- Kamera ----------------
    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1920, 1080))
        self.camera.size_hint = (1, .8)
        self.camera.pos_hint = {"center_x": .5, "y": .2}
        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.camera.center)
        with self.camera.canvas.after:
            PopMatrix()
        self.camera.bind(pos=self.update_rot, size=self.update_rot)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    # ---------------- Capture Button ----------------
    def build_capture_button(self):
        self.capture = Button(
            size_hint=(None, None),
            size=(dp(70), dp(70)),
            pos_hint={"center_x": .5, "y": .05},
            background_normal="",
            background_color=(0,0,0,0)
        )
        with self.capture.canvas.before:
            Color(1,1,1,1)
            self.outer_circle = Ellipse(size=self.capture.size, pos=self.capture.pos)
        self.capture.bind(pos=self.update_circle, size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)
        self.add_widget(self.capture)

    def update_circle(self, *args):
        self.outer_circle.pos = self.capture.pos
        self.outer_circle.size = self.capture.size

    # ---------------- Fotos ----------------
    def get_next_number(self):
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        return f"{len(files)+1:04d}"

    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number + ".png")
        self.camera.export_to_png(path)

        # Overlay "Norden" oder Winkel
        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False
        if arduino_on:
            # Hier könnte man echten Sensorwert einsetzen
            # Für Simulation nutzen wir self.orientation_angle
            overlay_angle = int(self.orientation_angle)
        else:
            overlay_angle = None

        # Vorschau nach Aufnahme
        self.show_preview(path, overlay_angle)

    def show_preview(self, path, overlay_angle=None):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = FloatLayout()
        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)

        if overlay_angle is not None:
            overlay_label = Label(
                text=f"Winkel: {overlay_angle}°" if overlay_angle is not None else "Norden",
                font_size=40, color=(1,0,0,1),
                pos_hint={"top": 0.95, "center_x": 0.5}
            )
            layout.add_widget(overlay_label)

        # Capture Button weiterhin unten
        layout.add_widget(self.capture)
        self.add_widget(layout)

    # ---------------- Galerie ----------------
    def show_gallery(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        if not files:
            self.add_widget(Label(text="Keine Fotos", font_size=24, pos_hint={"center_x":0.5,"center_y":0.5}))
            return

        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=10, padding=[10, 120,10,10], size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for file in files:
            try:
                box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(280), spacing=5)
                img = Image(source=os.path.join(self.photos_dir, file), allow_stretch=True)
                img.bind(on_touch_down=lambda inst, touch, f=file: self.open_image_safe(f, touch))
                name_label = Label(text=file.replace(".png",""), size_hint_y=None, height=dp(25))
                box.add_widget(img)
                box.add_widget(name_label)
                grid.add_widget(box)
            except Exception as e:
                print("Fehler Galerie Foto:", e)
        scroll.add_widget(grid)
        self.add_widget(scroll)

    def open_image_safe(self, filename, touch):
        try:
            img_widget = Image(source=os.path.join(self.photos_dir, filename), allow_stretch=True)
            if img_widget.collide_point(*touch.pos):
                self.open_image(filename)
        except Exception as e:
            print("Fehler beim Öffnen:", e)

    def open_image(self, filename):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = FloatLayout()
        img = Image(source=os.path.join(self.photos_dir, filename), allow_stretch=True)
        layout.add_widget(img)

        # Overlay Winkel/Norden
        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False
        overlay_label = Label(
            text="Norden" if not arduino_on else f"Winkel: {int(self.orientation_angle)}°",
            font_size=40, color=(1,0,0,1),
            pos_hint={"top":0.95,"center_x":0.5}
        )
        layout.add_widget(overlay_label)

        # i-Button nur in Einzelansicht
        info_btn = Button(text="i", size_hint=(None,None), size=(dp(40),dp(40)), pos_hint={"top":0.9,"right":0.95})
        info_btn.bind(on_press=lambda x: self.show_info(filename))
        layout.add_widget(info_btn)

        self.add_widget(layout)

    def show_info(self, filename):
        path = os.path.join(self.photos_dir, filename)
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        name_input = TextInput(text=filename.replace(".png",""), multiline=False)
        box.add_widget(Label(text="Name ändern:"))
        box.add_widget(name_input)
        timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        box.add_widget(Label(text=f"Datum/Uhrzeit:\n{timestamp}"))
        save_btn = Button(text="Speichern")
        save_btn.bind(on_press=lambda x: self.rename_file(filename,name_input.text))
        box.add_widget(save_btn)
        delete_btn = Button(text="Foto löschen")
        delete_btn.bind(on_press=lambda x: self.delete_file_safe(filename))
        box.add_widget(delete_btn)
        popup = Popup(title=filename.replace(".png",""), content=box, size_hint=(0.8,0.7))
        popup.open()

    def delete_file_safe(self, filename):
        try:
            os.remove(os.path.join(self.photos_dir, filename))
        except Exception as e:
            print(e)
        finally:
            self.show_gallery()

    def rename_file(self, old_name, new_name):
        os.rename(os.path.join(self.photos_dir, old_name), os.path.join(self.photos_dir, f"{new_name}.png"))
        self.show_gallery()

    # ---------------- A-Seite ----------------
    def show_a(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        if not hasattr(self, "a_label"):
            self.a_label = Label(text="NORD: 0°\nN", font_size=40, pos_hint={"center_x":0.5,"center_y":0.5})
            self.add_widget(self.a_label)

    def update_a_page(self, dt):
        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False
        if hasattr(self, "a_label"):
            self.a_label.text = f"NORD: {int(self.orientation_angle)}°\nNO"

    # ---------------- Settings ----------------
    def show_settings(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = BoxLayout(orientation="vertical", spacing=20, padding=[20,20,20,20])
        layout.add_widget(Label(text="Einstellungen", font_size=32, size_hint_y=None, height=dp(60)))
        def create_toggle_row(text,key):
            row = BoxLayout(size_hint_y=None,height=dp(60))
            label = Label(text=text)
            btn_ja = Button(text="Ja", size_hint=(None,None), size=(dp(80),dp(45)))
            btn_nein = Button(text="Nein", size_hint=(None,None), size=(dp(80),dp(45)))
            value = self.store.get(key)["value"] if self.store.exists(key) else False
            def update(selected):
                if selected:
                    btn_ja.background_color=(0,0.6,0,1)
                    btn_nein.background_color=(1,1,1,1)
                else:
                    btn_nein.background_color=(0,0.6,0,1)
                    btn_ja.background_color=(1,1,1,1)
            update(value)
            btn_ja.bind(on_press=lambda x:[self.store.put(key,value=True),update(True)])
            btn_nein.bind(on_press=lambda x:[self.store.put(key,value=False),update(False)])
            row.add_widget(label)
            row.add_widget(btn_ja)
            row.add_widget(btn_nein)
            return row
        layout.add_widget(create_toggle_row("Mit Arduino Daten","arduino"))
        layout.add_widget(create_toggle_row("Automatisch speichern","auto"))
        self.add_widget(layout)

    # ---------------- Hilfe ----------------
    def show_help(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Bei Fragen wenden Sie sich bitte per E-Mail an Support.", font_size=20,pos_hint={"center_x":0.5,"center_y":0.5}))

# ---------------- Main ----------------
class MainApp(App):
    def build(self):
        return Dashboard()

if __name__=="__main__":
    MainApp().run()
