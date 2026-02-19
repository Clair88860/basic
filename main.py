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
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window


# ==========================================================
# Verschiebbare Eckpunkte
# ==========================================================
class DraggableCorner(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (60, 60)
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
            if hasattr(self.parent, "update_lines"):
                self.parent.update_lines()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self.dragging = False
        return super().on_touch_up(touch)


# ==========================================================
# Dashboard
# ==========================================================
class Dashboard(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.store = JsonStore("settings.json")
        if not self.store.exists("settings"):
            self.store.put("settings", entzerrung=False, arduino=False, auto=False)

        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        self.current_angle = 0
        Clock.schedule_interval(self.update_angle, 1)

        self.build_topbar()
        self.build_camera()
        self.build_capture_button()

        Clock.schedule_once(lambda dt: self.show_camera(), 0.2)

    # ======================================================
    # Arduino Simulation
    # ======================================================
    def update_angle(self, dt):
        self.current_angle = (self.current_angle + 5) % 360

    # ======================================================
    # Topbar
    # ======================================================
    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top":1})

        btn_k = Button(text="K")
        btn_g = Button(text="G")
        btn_e = Button(text="E")
        btn_a = Button(text="A")
        btn_h = Button(text="H")

        btn_k.bind(on_press=self.show_camera)
        btn_g.bind(on_press=self.show_gallery)
        btn_e.bind(on_press=self.show_settings)
        btn_a.bind(on_press=self.show_a)
        btn_h.bind(on_press=self.show_help)

        for btn in [btn_k, btn_g, btn_e, btn_a, btn_h]:
            self.topbar.add_widget(btn)

        self.add_widget(self.topbar)

    # ======================================================
    # Kamera
    # ======================================================
    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1280, 720))
        self.camera.size_hint = (1, .9)
        self.camera.pos_hint = {"center_x":.5,"center_y":.45}

        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90)
        with self.camera.canvas.after:
            PopMatrix()

        self.camera.bind(pos=self.update_rotation,
                         size=self.update_rotation)

    def update_rotation(self, *args):
        self.rot.origin = self.camera.center

    # ======================================================
    # Kamera Button (FIX)
    # ======================================================
    def build_capture_button(self):
        self.capture = Button(size_hint=(None,None),
                              size=(dp(70),dp(70)),
                              pos_hint={"center_x":.5,"y":.04},
                              background_normal="",
                              background_color=(0,0,0,0))

        with self.capture.canvas.before:
            Color(1,1,1,1)
            self.circle = Ellipse(size=self.capture.size,
                                  pos=self.capture.pos)

        self.capture.bind(pos=self.update_circle,
                          size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self,*args):
        self.circle.pos = self.capture.pos
        self.circle.size = self.capture.size

    # ======================================================
    # Kamera anzeigen
    # ======================================================
    def show_camera(self,*args):
        Clock.unschedule(self.update_a_label)

        self.clear_widgets()
        self.add_widget(self.topbar)

        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

        if self.store.get("settings")["entzerrung"]:
            self.init_overlay()

    # ======================================================
    # Overlay nur Kamera
    # ======================================================
    def init_overlay(self):
        self.corners = []
        w,h = Window.width, Window.height

        pad_x, pad_y = w*0.2, h*0.25
        positions = [(pad_x,h-pad_y),(w-pad_x,h-pad_y),
                     (w-pad_x,pad_y),(pad_x,pad_y)]

        for pos in positions:
            c = DraggableCorner(pos=(pos[0]-30,pos[1]-30))
            self.add_widget(c)
            self.corners.append(c)

        with self.canvas:
            Color(0,1,0,1)
            self.line = Line(width=3)

        self.update_lines()

    def update_lines(self):
        pts=[]
        for i in [0,1,2,3,0]:
            pts.extend([self.corners[i].center_x,
                        self.corners[i].center_y])
        self.line.points=pts

    # ======================================================
    # Perspektive (FIX)
    # ======================================================
    def apply_perspective(self,path):
        img = cv2.imread(path)
        if img is None:
            return path

        h_real,w_real = img.shape[:2]

        mapped=[]
        for c in self.corners:
            x=(c.center_x/Window.width)*w_real
            y=h_real-(c.center_y/Window.height)*h_real
            mapped.append([x,y])

        pts = np.array(mapped,dtype="float32")

        dst=np.array([[0,0],
                      [w_real,0],
                      [w_real,h_real],
                      [0,h_real]],dtype="float32")

        M=cv2.getPerspectiveTransform(pts,dst)
        warped=cv2.warpPerspective(img,M,(w_real,h_real))

        new_path = os.path.join(self.photos_dir,"warped_temp.png")
        cv2.imwrite(new_path,warped)

        return new_path

    # ======================================================
    # Foto
    # ======================================================
    def take_photo(self, instance):
        number = f"{len([f for f in os.listdir(self.photos_dir) if f.endswith('.png')])+1:04d}"
        temp_path = os.path.join(self.photos_dir,"temp.png")
        self.camera.export_to_png(temp_path)

        final_path = temp_path

        if self.store.get("settings")["entzerrung"]:
            final_path = self.apply_perspective(temp_path)

        self.show_preview(final_path, number)

    # ======================================================
    # Vorschau
    # ======================================================
    def show_preview(self,path,number):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = FloatLayout()
        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)

        save_btn = Button(text="Speichern",
                          size_hint=(.4,.1),
                          pos_hint={"x":.05,"y":.02})
        retry_btn = Button(text="Wiederholen",
                           size_hint=(.4,.1),
                           pos_hint={"right":.95,"y":.02})

        def save(instance):
            final=os.path.join(self.photos_dir,number+".png")
            os.rename(path,final)

            if self.store.get("settings")["arduino"]:
                self.store.put(number,
                               angle=self.current_angle,
                               timestamp=str(datetime.datetime.now()))

            self.show_gallery()

        retry_btn.bind(on_press=lambda x: self.show_camera())
        save_btn.bind(on_press=save)

        layout.add_widget(save_btn)
        layout.add_widget(retry_btn)

        if self.store.get("settings")["arduino"]:
            overlay = Label(text=f"NORD: {int(self.current_angle)}°",
                            pos_hint={"right":.98,"top":.95})
            layout.add_widget(overlay)

        self.add_widget(layout)

    # ======================================================
    # A-Seite Live
    # ======================================================
    def show_a(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)

        layout = FloatLayout()
        self.a_label = Label(font_size=28,
                             pos_hint={"center_x":.5,"center_y":.5})
        layout.add_widget(self.a_label)

        self.add_widget(layout)

        Clock.schedule_interval(self.update_a_label,1)

    def update_a_label(self,dt):
        if self.store.get("settings")["arduino"]:
            self.a_label.text=f"Aktueller Nord-Wert:\n{int(self.current_angle)}°"
        else:
            self.a_label.text="Arduino deaktiviert"

    # ======================================================
    # Rest unverändert
    # ======================================================
    def show_gallery(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Galerie"))

    def show_help(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Help"))

    def show_settings(self,*args):
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Settings"))


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
