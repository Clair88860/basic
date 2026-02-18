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
from kivy.uix.camera import Camera
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp
from kivy.clock import Clock


class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")

        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        # Simulierter Nord-Winkel
        self.current_angle = 0
        Clock.schedule_interval(self.update_angle, 0.5)

        self.build_topbar()
        self.build_camera()
        self.build_capture_button()

        Clock.schedule_once(lambda dt: self.show_camera(), 0.2)

    # -------------------------------------------------
    # Nord Simulation
    # -------------------------------------------------
    def update_angle(self, dt):
        self.current_angle = (self.current_angle + 10) % 360

    def get_direction(self, angle):
        dirs = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]
        return dirs[int((angle + 22.5) / 45) % 8]

    # -------------------------------------------------
    # Dashboard oben
    # -------------------------------------------------
    def build_topbar(self):
        self.topbar = BoxLayout(
            size_hint=(1, .08),
            pos_hint={"top": 1},
            spacing=5,
            padding=5
        )

        for t, f in [
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("A", self.show_a)
        ]:
            b = Button(text=t)
            b.bind(on_press=f)
            self.topbar.add_widget(b)

        self.add_widget(self.topbar)

    # -------------------------------------------------
    # Kamera
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
        self.capture = Button(
            size_hint=(None, None),
            size=(dp(70), dp(70)),
            pos_hint={"center_x": .5, "y": .04},
            background_normal="",
            background_color=(0, 0, 0, 0)
        )

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
    # Foto aufnehmen
    # -------------------------------------------------
    def take_photo(self, instance):
        number = self.get_next_number()
        path = os.path.join(self.photos_dir, number + ".png")

        self.camera.export_to_png(path)

        # Winkel speichern
        self.store.put(number, angle=self.current_angle)

        self.show_preview(path, number)

    def get_next_number(self):
        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        return f"{len(files)+1:04d}"

    # -------------------------------------------------
    # Einzelansicht mit I Button
    # -------------------------------------------------
    def show_preview(self, path, number):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = FloatLayout()

        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)

        # Winkel Overlay anzeigen
        if self.store.exists(number):
            angle = self.store.get(number)["angle"]
            direction = self.get_direction(angle)

            overlay = Label(
                text=f"NORD: {int(angle)}°\n{direction}",
                pos_hint={"right": .98, "top": .95},
                size_hint=(None, None),
                size=(200, 100)
            )
            layout.add_widget(overlay)

        # I Button
        info_btn = Button(
            text="i",
            size_hint=(None, None),
            size=(50, 50),
            pos_hint={"x": .02, "top": .95}
        )

        info_btn.bind(on_press=lambda x: self.show_info_popup(number))
        layout.add_widget(info_btn)

        # Zurück Button
        back = Button(
            text="Zurück",
            size_hint=(1, .1),
            pos_hint={"y": 0}
        )
        back.bind(on_press=self.show_gallery)

        layout.add_widget(back)

        self.add_widget(layout)

    def show_info_popup(self, number):
        if not self.store.exists(number):
            return

        angle = self.store.get(number)["angle"]
        direction = self.get_direction(angle)

        content = Label(text=f"Winkel: {int(angle)}°\nRichtung: {direction}")

        popup = Popup(
            title="Foto Information",
            content=content,
            size_hint=(.7, .4)
        )
        popup.open()

    # -------------------------------------------------
    # Galerie
    # -------------------------------------------------
    def show_gallery(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])

        if not files:
            self.add_widget(Label(
                text="Keine Fotos vorhanden",
                pos_hint={"center_x": .5, "center_y": .5}
            ))
            return

        scroll = ScrollView()
        grid = GridLayout(cols=2,
                          spacing=10,
                          padding=10,
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for file in files:
            number = file.replace(".png", "")
            path = os.path.join(self.photos_dir, file)

            btn = Button(size_hint_y=None, height=200)
            img = Image(source=path, allow_stretch=True)
            btn.add_widget(img)

            btn.bind(on_press=lambda x, p=path, n=number:
                     self.show_preview(p, n))

            grid.add_widget(btn)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    # -------------------------------------------------
    # Seite A
    # -------------------------------------------------
    def show_a(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = FloatLayout()

        self.a_label = Label(
            text="",
            font_size=40,
            pos_hint={"center_x": .5, "center_y": .55}
        )

        layout.add_widget(self.a_label)
        self.add_widget(layout)

        Clock.schedule_interval(self.update_a_display, 0.5)

    def update_a_display(self, dt):
        direction = self.get_direction(self.current_angle)
        self.a_label.text = f"NORD: {int(self.current_angle)}°\n{direction}"


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
