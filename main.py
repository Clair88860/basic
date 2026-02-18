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


class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")
        self.meta = JsonStore("meta.json")

        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        # Simulierter Arduino Winkel
        self.current_angle = 0
        Clock.schedule_interval(self.simulate_angle, 0.5)

        self.build_topbar()
        self.build_camera()
        self.build_capture_button()

        Clock.schedule_once(lambda dt: self.show_camera(), 0.2)

    # -------------------------------------------------
    # Simulation Arduino
    # -------------------------------------------------
    def simulate_angle(self, dt):
        self.current_angle = (self.current_angle + 10) % 360

    def get_direction(self, angle):
        dirs = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]
        return dirs[int((angle + 22.5) / 45) % 8]

    # -------------------------------------------------
    # DASHBOARD
    # -------------------------------------------------
    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top": 1})

        for t, f in [
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings),
            ("A", self.show_a),
            ("H", self.show_help)
        ]:
            b = Button(text=t)
            b.bind(on_press=f)
            self.topbar.add_widget(b)

        self.add_widget(self.topbar)

    # -------------------------------------------------
    # KAMERA
    # -------------------------------------------------
    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1280, 720))
        self.camera.size_hint = (1, .9)
        self.camera.pos_hint = {"center_x": .5, "center_y": .45}

        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(pos=self.update_rot, size=self.update_rot)

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    def build_capture_button(self):
        self.capture = Button(size_hint=(None, None),
                              size=(dp(70), dp(70)),
                              pos_hint={"center_x": .5, "y": .04},
                              background_normal="",
                              background_color=(0, 0, 0, 0))

        with self.capture.canvas.before:
            Color(1, 1, 1, 1)
            self.circle = Ellipse(size=self.capture.size,
                                  pos=self.capture.pos)

        self.capture.bind(pos=self.update_circle,
                          size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self, *args):
        self.circle.pos = self.capture.pos
        self.circle.size = self.capture.size

    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

    # -------------------------------------------------
    # FOTO
    # -------------------------------------------------
    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number + ".png")

        self.camera.export_to_png(path)

        timestamp = datetime.datetime.now()

        self.meta.put(number,
                      date=str(timestamp),
                      angle=self.current_angle)

        auto = self.store.get("auto")["value"] if self.store.exists("auto") else False

        if auto:
            self.show_gallery()
        else:
            self.show_preview(path)

    def show_preview(self, path):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical")

        layout.add_widget(Image(source=path, allow_stretch=True))

        btns = BoxLayout(size_hint_y=0.2)
        save = Button(text="Speichern")
        repeat = Button(text="Wiederholen")

        save.bind(on_press=lambda x: self.show_gallery())
        repeat.bind(on_press=lambda x: self.show_camera())

        btns.add_widget(save)
        btns.add_widget(repeat)
        layout.add_widget(btns)

        self.add_widget(layout)

    def get_next_number(self):
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        return f"{len(files)+1:04d}"

    # -------------------------------------------------
    # GALERIE
    # -------------------------------------------------
    def show_gallery(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])

        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=10, padding=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for file in files:
            box = BoxLayout(orientation="vertical",
                            size_hint_y=None,
                            height=dp(250))

            img = Image(source=os.path.join(self.photos_dir, file),
                        allow_stretch=True)

            img.bind(on_touch_down=lambda inst, touch, f=file:
                     self.open_image(f) if inst.collide_point(*touch.pos) else None)

            name = Label(text=file.replace(".png", ""),
                         size_hint_y=None,
                         height=dp(25))

            box.add_widget(img)
            box.add_widget(name)
            grid.add_widget(box)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    # -------------------------------------------------
    # EINZELANSICHT
    # -------------------------------------------------
    def open_image(self, filename):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical")

        img_layout = FloatLayout(size_hint_y=0.85)

        path = os.path.join(self.photos_dir, filename)
        img = Image(source=path, allow_stretch=True)
        img_layout.add_widget(img)

        # Overlay nur wenn Arduino aktiv
        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False
        if arduino_on and self.meta.exists(filename.replace(".png", "")):
            angle = self.meta.get(filename.replace(".png", ""))["angle"]
            direction = self.get_direction(angle)

            overlay = Label(
                text=f"NORD {int(angle)}° {direction}",
                pos_hint={"right": .98, "top": .95},
                color=(1, 0, 0, 1),
                font_size=20
            )
            img_layout.add_widget(overlay)

        layout.add_widget(img_layout)

        bottom = BoxLayout(size_hint_y=0.15)

        name_lbl = Label(text=filename.replace(".png", ""))

        info_btn = Button(text="i",
                          size_hint=(None, None),
                          size=(dp(40), dp(40)))
        info_btn.bind(on_press=lambda x: self.show_info(filename))

        bottom.add_widget(name_lbl)
        bottom.add_widget(info_btn)

        layout.add_widget(bottom)
        self.add_widget(layout)

    # -------------------------------------------------
    # INFO POPUP
    # -------------------------------------------------
    def show_info(self, filename):
        number = filename.replace(".png", "")
        path = os.path.join(self.photos_dir, filename)

        box = BoxLayout(orientation="vertical", padding=10, spacing=10)

        box.add_widget(Label(text=f"Name: {number}"))

        timestamp = self.meta.get(number)["date"]
        box.add_widget(Label(text=f"Datum:\n{timestamp}"))

        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False
        if arduino_on:
            angle = self.meta.get(number)["angle"]
            direction = self.get_direction(angle)
            box.add_widget(Label(text=f"Winkel: {int(angle)}° {direction}"))

        delete_btn = Button(text="Foto löschen")
        delete_btn.bind(on_press=lambda x: self.delete_confirm(filename))
        box.add_widget(delete_btn)

        Popup(title="Info",
              content=box,
              size_hint=(0.8, 0.6)).open()

    def delete_confirm(self, filename):
        box = BoxLayout(orientation="vertical")
        box.add_widget(Label(text="Wirklich löschen?"))

        yes = Button(text="Ja")
        no = Button(text="Nein")

        box.add_widget(yes)
        box.add_widget(no)

        popup = Popup(content=box, size_hint=(0.6, 0.4))
        yes.bind(on_press=lambda x: [self.delete_file(filename), popup.dismiss()])
        no.bind(on_press=lambda x: popup.dismiss())
        popup.open()

    def delete_file(self, filename):
        os.remove(os.path.join(self.photos_dir, filename))
        self.meta.delete(filename.replace(".png", ""))
        self.show_gallery()

    # -------------------------------------------------
    # A SEITE
    # -------------------------------------------------
    def show_a(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        arduino_on = self.store.get("arduino")["value"] if self.store.exists("arduino") else False

        if arduino_on:
            self.label = Label(font_size=40,
                               pos_hint={"center_x": .5, "center_y": .5})
            self.add_widget(self.label)
            Clock.schedule_interval(self.update_a, 0.5)
        else:
            self.add_widget(Label(
                text="Arduino Daten nicht aktiviert",
                font_size=30,
                pos_hint={"center_x": .5, "center_y": .5}
            ))

    def update_a(self, dt):
        direction = self.get_direction(self.current_angle)
        self.label.text = f"NORD {int(self.current_angle)}°\n{direction}"

    # -------------------------------------------------
    # H SEITE
    # -------------------------------------------------
    def show_help(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(
            text="Hier steht dauerhaft dein Hilfetext.",
            pos_hint={"center_x": .5, "center_y": .5}
        ))

    # -------------------------------------------------
    # EINSTELLUNGEN
    # -------------------------------------------------
    def show_settings(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical", padding=20, spacing=20)

        def toggle(text, key):
            row = BoxLayout(size_hint_y=None, height=dp(50))
            label = Label(text=text)

            btn_ja = Button(text="Ja")
            btn_nein = Button(text="Nein")

            value = self.store.get(key)["value"] if self.store.exists(key) else False

            def update(v):
                btn_ja.background_color = (0,1,0,1) if v else (1,1,1,1)
                btn_nein.background_color = (0,1,0,1) if not v else (1,1,1,1)

            update(value)

            btn_ja.bind(on_press=lambda x: [self.store.put(key, value=True), update(True)])
            btn_nein.bind(on_press=lambda x: [self.store.put(key, value=False), update(False)])

            row.add_widget(label)
            row.add_widget(btn_ja)
            row.add_widget(btn_nein)
            return row

        layout.add_widget(toggle("Mit Arduino Daten", "arduino"))
        layout.add_widget(toggle("Automatisch speichern", "auto"))

        self.add_widget(layout)


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
