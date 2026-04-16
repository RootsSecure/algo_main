import json
import time
import threading
import paho.mqtt.client as mqtt
from jnius import autoclass
from kivy.app import App
from kivy.clock import mainthread

from db_manager import DBManager

class CommunicationManager:
    """
    Manages robust networking (MQTT) and IPC (Kivy -> Kotlin).
    Contains auto-reconnect fallback mechanisms and triggers DB/UI layers.
    """
    def __init__(self, broker_address, alert_handler=None):
        self.broker_address = broker_address
        self.topic = "sentinel/plot/+/alerts"  # Dynamic wildcard for plot alerts
        self.alert_handler = alert_handler
        self.db = DBManager()
        
        self.client = mqtt.Client(client_id="NRI_Android_Client_01")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        self.connected = False
        self.reconnect_delay = 1  # Initial backoff delay (seconds)

    def start(self):
        """Runs the MQTT network loop in a background thread."""
        thread = threading.Thread(target=self._connect_and_loop, daemon=True)
        thread.start()

    def _connect_and_loop(self):
        while True:
            try:
                print(f"Connecting to MQTT broker at {self.broker_address}...")
                self.client.connect(self.broker_address, port=1883, keepalive=60)
                self.client.loop_forever()
            except Exception as e:
                print(f"Connection failed: {e}. Retrying in {self.reconnect_delay}s...")
                time.sleep(self.reconnect_delay)
                # Exponential backoff maxing out at 60 seconds
                self.reconnect_delay = min(self.reconnect_delay * 2, 60)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected! Subscribing to: {self.topic}")
            self.connected = True
            self.reconnect_delay = 1  # Reset exponent on success
            self.client.subscribe(self.topic, qos=1)
            
            # Refresh UI heartbeat
            if self.alert_handler:
                self.alert_handler.receive_heartbeat()
        else:
            print(f"Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        print(f"Disconnected from broker (Code: {rc})")
        self.connected = False

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8')
        try:
            event = json.loads(payload)
            
            # Parse Event Keys
            alert_id = event.get('id', f"evt_{int(time.time())}")
            alert_type = event.get('type', 'UNKNOWN')
            level = event.get('level', 'INFO')
            timestamp = event.get('timestamp', str(time.time()))
            
            # (In production, execute HTTP download of visual proof to this local path)
            # local_image_path = f"/data/user/0/org.nri.sentinel/files/ev_{alert_id}.jpg"
            local_image_path = ""
            
            # 1. Local Persistence (First Operation)
            self.db.save_alert(
                alert_id, alert_type, level, timestamp, local_image_path, payload
            )
            
            # 2. UI Update (Second Operation)
            if self.alert_handler:
                @mainthread
                def invoke_ui():
                    self.alert_handler.handle_incoming_alert(payload)
                invoke_ui()
                
        except json.JSONDecodeError:
            print("Dropped malformed MQTT payload")

    @staticmethod
    def trigger_critical_live_feed():
        """
        Inter-Process Communication: Kivy -> native Kotlin Android Activity.
        Called when user taps "Live Feed" on a Critical Alert.
        
        PyJNIus Architecture Context:
        Because Kivy operates inside an embedded Python environment within Android, it cannot
        natively spawn an OS Activity. We utilize PyJNIus (autoclass) to dynamically bridge
        into the JVM at runtime. We fetch the active PythonActivity Context, construct a standard
        Java android.content.Intent, target our Native Kotlin class (LiveCameraActivity.kt), 
        and command the JVM to launch it. This enables high-performance Native Kotlin pipelines
        to seamlessly take over from the Python UI.
        """
        from kivy.utils import platform
        if platform == 'android':
            try:
                # Load necessary Java classes via JNIus
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                String = autoclass('java.lang.String')
                
                # Generate cross-activity intent launching to native Kotlin UI
                context = PythonActivity.mActivity
                intent = Intent()
                intent.setClassName("org.rootssecure.sentinel", "org.rootssecure.sentinel.LiveCameraActivity")
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                intent.putExtra(String("intent_source"), String("kivy_critical_response"))
                
                context.startActivity(intent)
                print("Success: PyJNIus launched LiveCameraActivity.kt")
            except Exception as e:
                print(f"JNI Bridge failure: {e}")
        else:
            print("OS not Android. Cannot bridge Native Activity.")
