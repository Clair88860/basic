
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
from kivy.uix.textinput import TextInput
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Line, Ellipse, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window

# ==========================================================
# Verschiebbare Eckpunkte für Entzerrung
# ==========================================================
class DraggableCorner(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (60, 60)
        self.background_color = (0, 1, 0, 0.7)
        self.dragging = False

    def on_touch_down(self, touch):
        if abs(touch.x - self.center_x) < 80 and abs(touch.y - self.center_y) < 80:
            self.dragging = True
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.dragging:
            x = min(max(0, touch.x - self.width/2), Window.width - self.width)
            y = min(max(0, touch.y - self.height/2), Window.height - self.height)
            self.pos = (x, y)
            if self.parent:
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
            self.store.put("settings", arduino=False, auto=False)

        app = App.get_running_app()
        self.photos_dir = os.path.join(app.user_data_dir, "photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        self.current_angle = 0
        Clock.schedule_interval(self.update_angle, 0.5)

        self.build_topbar()
        self.build_camera()
        self.build_capture_button()

        Clock.schedule_once(lambda dt: self.show_camera(), 0.2)

    # ======================================================
    # Simulierte Nord/Arduino Daten
    # ======================================================
    def update_angle(self, dt):
        self.current_angle = (self.current_angle + 10) % 360

    # ======================================================
    # Topbar
    # ======================================================
    def build_topbar(self):
        self.topbar = BoxLayout(size_hint=(1, .08), pos_hint={"top":1}, spacing=2, padding=2)

        btn_k = Button(background_normal="camera_icon.png", background_down="camera_icon.png",text="",size_hint=(None, None),size=(150, 150))
        btn_g = Button(
            background_normal="gallery_icon.png",
            background_down="gallery_icon.png",
            text="",
            size_hint=(None, None),
            size=(150, 150)
        )
        
        btn_e = Button(
            background_normal="settings_icon.png",
            background_down="settings_icon.png",
            text="",
            size_hint=(None, None),
            size=(150, 150)
        )

        btn_h = Button(
            background_normal="question_icon.png",
            background_down="question_icon.png",
            text="",
            size_hint=(None, None),
            size=(150, 150)
        )

        btn_k.bind(on_press=self.show_camera)
        btn_g.bind(on_press=self.show_gallery)
        btn_e.bind(on_press=self.show_settings)
        
        btn_h.bind(on_press=self.show_help)

        for btn in [btn_k, btn_g, btn_e, btn_h]:
            self.topbar.add_widget(btn)

        self.add_widget(self.topbar)

    # ======================================================
    # Kamera
    # ======================================================
    def build_camera(self):
        self.camera = Camera(play=False, resolution=(1280, 720))
        self.camera.size_hint = (1, .92)
        self.camera.pos_hint = {"top":.92}

        with self.camera.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90)
        with self.camera.canvas.after:
            PopMatrix()
        self.camera.bind(pos=self.update_rotation, size=self.update_rotation)

    def update_rotation(self, *args):
        self.rot.origin = self.camera.center

    # ------------------------------------------------------
    # Kamera Button
    # ------------------------------------------------------
    def build_capture_button(self):
        self.capture = Button(size_hint=(None,None), size=(dp(70),dp(70)),
                              pos_hint={"center_x":.5,"y":.04},
                              background_normal="", background_color=(0,0,0,0))
        with self.capture.canvas.before:
            Color(1,1,1,1)
            self.circle = Ellipse(size=self.capture.size,pos=self.capture.pos)
        self.capture.bind(pos=self.update_circle, size=self.update_circle)
        self.capture.bind(on_press=self.take_photo)

    def update_circle(self,*args):
        self.circle.pos = self.capture.pos
        self.circle.size = self.capture.size

    # ======================================================
    # Kamera anzeigen
    # ======================================================
    def show_camera(self,*args):
        self.remove_overlay()   # <- wichtig
        self.clear_widgets()
        self.add_widget(self.topbar)

        self.camera.play = True
        self.add_widget(self.camera)
        self.add_widget(self.capture)

        self.init_overlay()


    # ======================================================
    # Overlay Rahmen (nur auf K-Seite)
    # ======================================================
    def init_overlay(self):
        # Vorhandenen Overlay entfernen (falls vorhanden)
        if hasattr(self, "corners"):
            for c in self.corners:
                if c.parent:
                    self.remove_widget(c)
            self.corners = []
        if hasattr(self, "line"):
            try:
                self.canvas.remove(self.line)
            except:
                pass

        # Neuer Overlay
        self.corners = []
        w,h = Window.width, Window.height
        pad_x, pad_y = w*0.15, h*0.2
        positions = [(pad_x,h-pad_y),(w-pad_x,h-pad_y),(w-pad_x,pad_y),(pad_x,pad_y)]
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
            pts.extend([self.corners[i].center_x, self.corners[i].center_y])
        self.line.points=pts


        # ======================================================
    # Overlay komplett entfernen
    # ======================================================
    def remove_overlay(self):
        if hasattr(self, "corners"):
            for c in self.corners:
                if c.parent:
                    self.remove_widget(c)
            self.corners = []

        if hasattr(self, "line"):
            try:
                self.canvas.remove(self.line)
            except:
                pass

    # ======================================================
    # Foto aufnehmen
    # ======================================================
    def take_photo(self, instance):

        # Nur Hauptnummern zählen (ohne _I)
        existing = [f for f in os.listdir(self.photos_dir)
                    if f.endswith(".png") and "_I" not in f]

        number = f"{len(existing)+1:04d}"

        # Temporär speichern
        temp_path = os.path.join(self.photos_dir, "temp.png")
        self.camera.export_to_png(temp_path)

        # Entzerren
        warped_path = self.apply_perspective(temp_path)

        # Zielnamen
        final_main = os.path.join(self.photos_dir, number + ".png")
        final_i = os.path.join(self.photos_dir, number + "_I.png")

        # Entzerrtes Bild zweimal speichern
        import shutil
        shutil.copy(warped_path, final_main)
        shutil.copy(warped_path, final_i)

        # Temp löschen
        os.remove(temp_path)
        os.remove(warped_path)

        # Vorschau vom Hauptbild
        self.show_preview(final_main, number)


    # ======================================================
    # Perspektivische Transformation
    # ======================================================
    def apply_perspective(self,path):
        img = cv2.imread(path)
        if img is None: return path
        h_real,w_real = img.shape[:2]
        mapped=[]
        for c in self.corners:
            x=(c.center_x/Window.width)*w_real
            y=h_real-(c.center_y/Window.height)*h_real
            mapped.append([x,y])
        pts = np.array(mapped,dtype="float32")
        rect=np.zeros((4,2),dtype="float32")
        s = pts.sum(axis=1)
        rect[0]=pts[np.argmin(s)]
        rect[2]=pts[np.argmax(s)]
        diff=np.diff(pts,axis=1)
        rect[1]=pts[np.argmin(diff)]
        rect[3]=pts[np.argmax(diff)]
        (tl,tr,br,bl)=rect
        widthA = np.linalg.norm(br-bl)
        widthB = np.linalg.norm(tr-tl)
        maxWidth = int(max(widthA,widthB))
        heightA = np.linalg.norm(tr-br)
        heightB = np.linalg.norm(tl-bl)
        maxHeight = int(max(heightA,heightB))
        dst=np.array([[0,0],[maxWidth-1,0],[maxWidth-1,maxHeight-1],[0,maxHeight-1]],dtype="float32")
        M=cv2.getPerspectiveTransform(rect,dst)
        warped=cv2.warpPerspective(img,M,(maxWidth,maxHeight))
        new_path = os.path.join(self.photos_dir,"warped_temp.png")
        cv2.imwrite(new_path,warped)
        return new_path

    # ======================================================
    # Vorschau
    # ======================================================
    def show_preview(self,path,number):
        self.remove_overlay()

        self.clear_widgets()
        self.add_widget(self.topbar)
        layout = FloatLayout()
        img = Image(source=path, allow_stretch=True)
        layout.add_widget(img)

        auto=self.store.get("settings")["auto"]

        if auto:
            final=os.path.join(self.photos_dir,number+".png")
            os.rename(path,final)
            if self.store.get("settings")["arduino"]:
                self.store.put(number, angle=self.current_angle, timestamp=str(datetime.datetime.now()))
            self.show_gallery()
            return

        save_btn = Button(text="Speichern", size_hint=(.4,.1), pos_hint={"x":.05,"y":.02})
        retry_btn = Button(text="Wiederholen", size_hint=(.4,.1), pos_hint={"right":.95,"y":.02})

        def save(instance):
            final=os.path.join(self.photos_dir,number+".png")
            os.rename(path,final)
            if self.store.get("settings")["arduino"]:
                self.store.put(number, angle=self.current_angle, timestamp=str(datetime.datetime.now()))
            self.show_gallery()

        def retry(instance):
            self.show_camera()

        save_btn.bind(on_press=save)
        retry_btn.bind(on_press=retry)
        layout.add_widget(save_btn)
        layout.add_widget(retry_btn)

        if self.store.get("settings")["arduino"]:
            overlay = Label(text=f"NORD: {int(self.current_angle)}°",
                            pos_hint={"right":.98,"top":.95})
            layout.add_widget(overlay)

        self.add_widget(layout)

    # ======================================================
    # Galerie
    # ======================================================
    def show_gallery(self,*args):
        self.remove_overlay()
        self.clear_widgets()
        self.add_widget(self.topbar)

        files = sorted([f for f in os.listdir(self.photos_dir) if f.endswith(".png")])
        if not files:
            self.add_widget(Label(text="Keine Fotos"))
            return

        scroll=ScrollView(size_hint=(1,1), pos_hint={"x":0,"y":0})
        grid=GridLayout(cols=2, spacing=10, padding=[10,60,10,10], size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for file in files:
            path=os.path.join(self.photos_dir,file)
            box=BoxLayout(orientation="vertical", size_hint_y=None, height=dp(280))
            img=Image(source=path, allow_stretch=True)
            img.bind(on_touch_down=lambda inst,touch,f=file:
                     self.show_single(f) if inst.collide_point(*touch.pos) else None)
            label=Label(text=file.replace(".png",""), size_hint_y=None,height=dp(25))
            box.add_widget(img)
            box.add_widget(label)
            grid.add_widget(box)

        scroll.add_widget(grid)
        self.add_widget(scroll)

    # ======================================================
    # Einzelansicht + i-Button + Löschen
    # ======================================================
    def show_single(self,filename):
        self.remove_overlay()

        self.clear_widgets()
        self.add_widget(self.topbar)
        layout=FloatLayout()
        path=os.path.join(self.photos_dir,filename)
        img=Image(source=path, allow_stretch=True)
        layout.add_widget(img)
        number=filename.replace(".png","")

        if self.store.exists(number) and self.store.get("settings")["arduino"]:
            data=self.store.get(number)
            angle=data.get("angle",0)
            timestamp=data.get("timestamp","")
            overlay = Label(text=f"NORD: {int(angle)}°", pos_hint={"right":.98,"top":.95})
            layout.add_widget(overlay)

            info_btn=Button(text="i",size_hint=(None,None),size=(50,50),pos_hint={"x":.02,"top":.95})
            def show_info(instance):
                box = BoxLayout(orientation="vertical", spacing=5)
                box.add_widget(Label(text=f"Name: {number}"))
                box.add_widget(Label(text=f"Datum: {timestamp}"))
                box.add_widget(Label(text=f"Winkel: {int(angle)}°"))

                delete_btn = Button(text="Foto löschen")
                def delete(instance):
                    os.remove(path)
                    self.show_gallery()
                    popup.dismiss()
                delete_btn.bind(on_press=delete)
                box.add_widget(delete_btn)

                popup = Popup(title="Info", content=box, size_hint=(0.8,0.7))
                popup.open()
            info_btn.bind(on_press=show_info)
            layout.add_widget(info_btn)

        self.add_widget(layout)

   
    # ======================================================
    # H-Seite
    # ======================================================
    def show_help(self,*args):
        self.remove_overlay()
        self.clear_widgets()
        self.add_widget(self.topbar)
        self.add_widget(Label(text="Bei Fragen oder Problemen:\nE-Mail", font_size=20,pos_hint={"center_x":.5,"center_y":.5}))

    # ======================================================
    # Einstellungen
    # ======================================================
    def show_settings(self,*args):
        self.remove_overlay()

        self.clear_widgets()
        self.add_widget(self.topbar)
        layout=BoxLayout(orientation="vertical", padding=[20,150,50,20], spacing=20)
        layout.add_widget(Label(text="Einstellungen", font_size=32, size_hint_y=None,height=dp(60)))

        def create_toggle_row(text,key):
            row=BoxLayout(size_hint_y=None,height=dp(60))
            label=Label(text=text)
            btn_ja=Button(text="Ja",size_hint=(None,None),size=(dp(80),dp(45)))
            btn_nein=Button(text="Nein",size_hint=(None,None),size=(dp(80),dp(45)))
            value=self.store.get("settings")[key]
            def update(selected):
                if selected:
                    btn_ja.background_color=(0,0.6,0,1)
                    btn_nein.background_color=(1,1,1,1)
                else:
                    btn_nein.background_color=(0,0.6,0,1)
                    btn_ja.background_color=(1,1,1,1)
            update(value)
            btn_ja.bind(on_press=lambda x:[self.store.put("settings", **{**self.store.get("settings"),key:True}), update(True)])
            btn_nein.bind(on_press=lambda x:[self.store.put("settings", **{**self.store.get("settings"),key:False}), update(False)])
            row.add_widget(label)
            row.add_widget(btn_ja)
            row.add_widget(btn_nein)
            return row

        
        layout.add_widget(create_toggle_row("Mit Winkel/Arduino Daten","arduino"))
        layout.add_widget(create_toggle_row("Automatisch speichern","auto"))

        self.add_widget(layout)


class MainApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    MainApp().run()
