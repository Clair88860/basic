import os
import cv2
import numpy as np
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
from kivy.graphics import Color, Line, Ellipse, PushMatrix, PopMatrix, Rotate
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp


# ==========================================================
# Verschiebbare Punkte für Entzerrung
# ==========================================================
class DraggableCorner(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (50, 50)
        self.background_color = (0, 1, 0, 0.7)
        self.dragging = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.dragging = True
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.dragging:
            self.center = touch.pos
            if self.parent:
                self.parent.update_lines()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self.dragging = False
        return super().on_touch_up(touch)


# ==========================================================
# HAUPT APP
# ==========================================================
class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")
        if not self.store.exists("settings"):
            self.store.put("settings",
                           arduino=False,
                           winkel=False,
                           entzerrung=False,
                           auto=False)

        self.photos_dir = os.path.join(App.get_running_app().user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        self.current_angle = 0
        Clock.schedule_interval(self.simulate_angle, 0.5)

        self.build_topbar()
        self.show_camera()

    # ======================================================
    # Simulation Arduino
    # ======================================================
    def simulate_angle(self, dt):
        if self.store.get("settings")["arduino"]:
            self.current_angle = (self.current_angle + 5) % 360

    # ======================================================
    # TOPBAR
    # ======================================================
    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top": 1})

        for name, func in [
            ("K", self.show_camera),
            ("G", self.show_gallery),
            ("E", self.show_settings),
            ("A", self.show_a),
            ("H", self.show_help)
        ]:
            btn = Button(text=name)
            btn.bind(on_press=func)
            self.topbar.add_widget(btn)

        self.add_widget(self.topbar)

    # ======================================================
    # KAMERA (groß!)
    # ======================================================
    def show_camera(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        self.camera = Camera(play=True, resolution=(1920, 1080))
        self.camera.size_hint = (1, .92)
        self.camera.pos_hint = {"x": 0, "y": 0}

        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(pos=self.update_rot, size=self.update_rot)

        self.add_widget(self.camera)

        # Entzerrungsrahmen nur hier
        if self.store.get("settings")["entzerrung"]:
            self.init_overlay()

        self.build_capture_button()

    def update_rot(self, *args):
        self.rot.origin = self.camera.center

    # ======================================================
    # Capture Button
    # ======================================================
    def build_capture_button(self):
        btn = Button(size_hint=(None, None),
                     size=(dp(80), dp(80)),
                     pos_hint={"center_x": .5, "y": .02},
                     background_normal="",
                     background_color=(0, 0, 0, 0))

        with btn.canvas.before:
            Color(1, 1, 1, 1)
            Ellipse(pos=btn.pos, size=btn.size)

        btn.bind(on_press=self.take_photo)
        self.add_widget(btn)

    # ======================================================
    # FOTO
    # ======================================================
    def take_photo(self, instance):
        number = f"{len(os.listdir(self.photos_dir)) + 1:04d}"
        path = os.path.join(self.photos_dir, number + ".png")

        self.camera.export_to_png(path)

        timestamp = str(datetime.datetime.now())

        # Daten speichern
        if self.store.get("settings")["arduino"] and self.store.get("settings")["winkel"]:
            self.store.put(number,
                           angle=self.current_angle,
                           timestamp=timestamp)

        self.preview_photo(path)

    # ======================================================
    # Vorschau → danach zurück zur K-Seite
    # ======================================================
    def preview_photo(self, path):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = FloatLayout()
        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)

        save = Button(text="Speichern",
                      size_hint=(.4, .1),
                      pos_hint={"x": .05, "y": .02})

        retry = Button(text="Wiederholen",
                       size_hint=(.4, .1),
                       pos_hint={"right": .95, "y": .02})

        save.bind(on_press=lambda x: self.show_camera())
        retry.bind(on_press=lambda x: self.show_camera())

        layout.add_widget(save)
        layout.add_widget(retry)

        self.add_widget(layout)

    # ======================================================
    # GALERIE (startet ab Mitte)
    # ======================================================
    def show_gallery(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        scroll = ScrollView(size_hint=(1, .5),
                            pos_hint={"x": 0, "y": 0})

        grid = GridLayout(cols=2,
                          spacing=10,
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        files = sorted(os.listdir(self.photos_dir))

        for file in files:
            path = os.path.join(self.photos_dir, file)
            img = Image(source=path,
                        size_hint_y=None,
                        height=dp(200))

            img.bind(on_touch_down=lambda inst, touch, f=file:
                     self.show_single(f) if inst.collide_point(*touch.pos) else None)

            grid.add_widget(img)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    # ======================================================
    # EINZELANSICHT
    # ======================================================
    def show_single(self, filename):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical")

        path = os.path.join(self.photos_dir, filename)
        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)

        bottom = BoxLayout(size_hint_y=.25)

        name_label = Label(text=filename.replace(".png", ""))

        info_btn = Button(text="i",
                          size_hint=(None, None),
                          size=(60, 60))

        bottom.add_widget(name_label)
        bottom.add_widget(info_btn)

        layout.add_widget(bottom)
        self.add_widget(layout)

        # Winkel Overlay nur hier
        number = filename.replace(".png", "")
        if self.store.exists(number):
            data = self.store.get(number)
            angle = data.get("angle", 0)
            overlay = Label(text=f"Winkel: {int(angle)}°",
                            pos_hint={"right": .95, "top": .95})
            layout.add_widget(overlay)

        # I BUTTON POPUP
        def show_info(instance):
            if not self.store.exists(number):
                return

            data = self.store.get(number)
            box = BoxLayout(orientation="vertical")

            box.add_widget(Label(text=f"Name: {number}"))
            box.add_widget(Label(text=f"Datum: {data['timestamp']}"))
            box.add_widget(Label(text=f"Winkel: {int(data['angle'])}°"))

            delete_btn = Button(text="Foto löschen")

            def confirm_delete(x):
                confirm = Popup(title="Sicher?",
                                content=Button(text="JA löschen",
                                               on_press=lambda y: self.delete_photo(path)),
                                size_hint=(.6, .4))
                confirm.open()

            delete_btn.bind(on_press=confirm_delete)

            box.add_widget(delete_btn)

            popup = Popup(title="Info",
                          content=box,
                          size_hint=(.8, .7))
            popup.open()

        info_btn.bind(on_press=show_info)

    def delete_photo(self, path):
        os.remove(path)
        self.show_gallery()

    # ======================================================
    # A SEITE
    # ======================================================
    def show_a(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        if self.store.get("settings")["arduino"]:
            label = Label(text=f"Simulation\nWinkel: {int(self.current_angle)}°",
                          font_size=30)
        else:
            label = Label(text="Arduino nicht aktiviert")

        self.add_widget(label)

    # ======================================================
    # H SEITE
    # ======================================================
    def show_help(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Hilfe Seite"))

    # ======================================================
    # EINSTELLUNGEN
    # ======================================================
    def show_settings(self, *args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = BoxLayout(orientation="vertical",
                           padding=20,
                           spacing=20)

        layout.add_widget(Label(text="Einstellungen", font_size=28))

        for text, key in [
            ("Mit Daten von Arduino", "arduino"),
            ("Mit Winkel", "winkel"),
            ("Mit Entzerrung", "entzerrung"),
            ("Automatisch speichern", "auto")
        ]:
            row = BoxLayout()

            label = Label(text=text)

            btn_ja = Button(text="Ja")
            btn_nein = Button(text="Nein")

            def make_toggle(k):
                return lambda x: self.toggle_setting(k, True)

            def make_toggle2(k):
                return lambda x: self.toggle_setting(k, False)

            btn_ja.bind(on_press=make_toggle(key))
            btn_nein.bind(on_press=make_toggle2(key))

            row.add_widget(label)
            row.add_widget(btn_ja)
            row.add_widget(btn_nein)

            layout.add_widget(row)

        self.add_widget(layout)

    def toggle_setting(self, key, value):
        settings = self.store.get("settings")
        settings[key] = value
        self.store.put("settings", **settings)
        self.show_settings()


# ==========================================================
# APP START
# ==========================================================
class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
