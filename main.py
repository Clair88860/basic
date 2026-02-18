from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.utils import platform
import math

if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity
    SensorManager = autoclass("android.hardware.SensorManager")
    Sensor = autoclass("android.hardware.Sensor")
    Context = autoclass("android.content.Context")
else:
    class PythonJavaClass: pass
    def java_method(sig): return lambda x: x

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

# ---------------- Sensor Listener ----------------
class OrientationListener(PythonJavaClass):
    __javainterfaces__ = ["android/hardware/SensorEventListener"]

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/hardware/SensorEvent;)V")
    def onSensorChanged(self, event):
        rotation = event.values
        if len(rotation) >= 3:
            R = [0]*9
            SensorManager.getRotationMatrixFromVector(R, rotation)
            orientation = SensorManager.getOrientation(R, [0.0,0.0,0.0])
            azimut = math.degrees(orientation[0])
            if azimut < 0:
                azimut += 360
            self.app.orientation = azimut

    @java_method("(Landroid/hardware/Sensor;I)V")
    def onAccuracyChanged(self, sensor, accuracy):
        pass

# ---------------- Main App ----------------
class CompassApp(App):
    def build(self):
        self.root = BoxLayout(orientation='vertical', padding=50)
        self.direction_label = Label(text="Richtung: Nord", font_size=80)
        self.angle_label = Label(text="0°", font_size=60)
        self.root.add_widget(self.direction_label)
        self.root.add_widget(self.angle_label)

        self.orientation = 0.0

        if platform == "android":
            self.sensor_manager = mActivity.getSystemService(Context.SENSOR_SERVICE)
            self.rotation_sensor = self.sensor_manager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)
            self.listener = OrientationListener(self)
            self.sensor_manager.registerListener(self.listener,
                                                 self.rotation_sensor,
                                                 SensorManager.SENSOR_DELAY_UI)

            Clock.schedule_interval(self.update_display, 0.2)

        return self.root

    def update_display(self, dt):
        dir_str = angle_to_direction(self.orientation)
        self.direction_label.text = f"Richtung: {dir_str}"
        self.angle_label.text = f"{int(self.orientation)}°"

    def on_stop(self):
        if platform == "android":
            self.sensor_manager.unregisterListener(self.listener)

if __name__ == "__main__":
    CompassApp().run()
