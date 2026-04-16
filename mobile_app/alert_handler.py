import json
import time
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.event import EventDispatcher

class AlertHandler(EventDispatcher):
    """
    Python/Kivy listener within the mobile app to handle incoming JSON alerts
    from the Raspberry Pi Sentinel Edge Node.
    """
    heartbeat_status = StringProperty("Standby")  # Transitions between "Armed" and "Standby"
    heartbeat_color = StringProperty("#696969")   # Dim Grey base
    last_heartbeat_time = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Check heartbeat state every 5 seconds
        Clock.schedule_interval(self.check_heartbeat, 5)
        
        # Windows Testing "Simulation Mode" Toggle
        from kivy.utils import platform
        self.simulation_mode = platform != 'android'
        if self.simulation_mode:
            print("[RootsSecure] Simulation Mode Active. Mocking MQTT payloads for Windows testing.")
            Clock.schedule_interval(self._simulate_mqtt_payload, 10)

    def _simulate_mqtt_payload(self, dt):
        """Generates fake 'RootsSecure' telemetry for Windows UI testing"""
        import random
        sim_payload = {
            "id": f"sim_{int(time.time())}",
            "type": random.choice(["SOIL_THEFT_ESCALATION", "ILLEGAL_CONSTRUCTION", "MOTION_DETECT"]),
            "level": random.choice(["HIGH", "CRITICAL", "INFO"]),
            "timestamp": str(time.time()),
            "metadata": {"duration_sec": random.randint(10, 120)},
            "has_visual_proof": True
        }
        self.handle_incoming_alert(json.dumps(sim_payload))
        
    def check_heartbeat(self, dt):
        """
        Since the Pi remains silent during no-motion periods, UI must show it's resting.
        If no data received for >60s, transition to Dim Grey (Standby).
        """
        if self.last_heartbeat_time == 0:
            return
            
        time_since_last = time.time() - self.last_heartbeat_time
        if time_since_last > 60:
            self.heartbeat_status = "Standby"
            self.heartbeat_color = "#696969" # Dim Grey
        else:
            self.heartbeat_status = "Armed"
            self.heartbeat_color = "#008080" # Teal
            
    def receive_heartbeat(self):
        """Updates timestamp and resets to Teal when any packet is received."""
        self.last_heartbeat_time = time.time()
        self.heartbeat_status = "Armed"
        self.heartbeat_color = "#008080" # Teal

    def handle_incoming_alert(self, json_payload):
        """
        Parses incoming JSON alert from the Pi. Maps the result to the UI.
        
        Note on Event Generation (The "5-Frame" Rule):
        To prevent false positives (like a bird flying past the motion gate), the Raspberry Pi
        logic engine utilizes a "5-frame" rule. It must confidently detect a specific object 
        (like a JCB or tractor) across 5 consecutive inferences before formulating the 
        CRITICAL/HIGH JSON payload transmitted here.
        """
        try:
            event = json.loads(json_payload)
            level = event.get("level")
            event_type = event.get("type")
            event_id = event.get("id")
            metadata = event.get("metadata", {})
            
            # Any activity counts as a heartbeat
            self.receive_heartbeat()
            
            # 1. Level Mapping Logic
            if level == "CRITICAL":
                self.trigger_critical_overlay()
            elif level == "HIGH":
                self.update_event_timeline(event, color="#FFBF00") # Amber pulse
                
            # 2. Payload Handling
            if event_type == "SOIL_THEFT_ESCALATION":
                duration_sec = metadata.get("duration_sec", 0)
                self.update_theft_tracker_counter(duration_sec)
                
            # 3. Visual Proof Integration for Edge Node Health Deep-Dive UI
            if event_id and event.get("has_visual_proof"):
                # Pair the event.id with the 1080p frame uploaded by the Pi
                image_url = f"https://api.sentinel-edge.com/evidence/{event_id}_1080p.jpg"
                self.load_visual_proof(image_url)
                
        except json.JSONDecodeError:
            print("AlertHandler Error: Failed to decode JSON payload")

    def trigger_critical_overlay(self):
        """Triggers full-screen Obsidian/Teal flashing overlay and high-priority sound."""
        # For simplicity, dispatching to root app widget
        app = App.get_running_app()
        if hasattr(app.root, 'show_critical_overlay'):
            app.root.show_critical_overlay()
        # NOTE: Implement Pyjnius Audio playback here for system sound
            
    def update_event_timeline(self, event, color_hex):
        """Updates Event timeline with new asymmetrical widget."""
        app = App.get_running_app()
        if hasattr(app.root, 'add_timeline_event'):
            app.root.add_timeline_event(event, color_hex)
            
    def update_theft_tracker_counter(self, duration_sec):
        """Live 'Time Since Detection' counter on Dashboard."""
        app = App.get_running_app()
        if hasattr(app.root, 'update_dashboard_counter'):
            app.root.update_dashboard_counter(duration_sec)
            
    def load_visual_proof(self, image_url):
        """
        Pushes image URL to the AsyncImage widget in our main.kv layout.
        
        Why AsyncImage? 
        The visual proofs are full 1080p files sent sequentially. Standard Image loading 
        operates on the main thread, which would aggressively stutter Kivy's UI rendering when
        fetching this payload. AsyncImage pushes the I/O read operation to a background thread,
        ensuring the Event Timeline continues scrolling smoothly.
        """
        app = App.get_running_app()
        if hasattr(app.root, 'set_visual_proof_image'):
            app.root.set_visual_proof_image(image_url)
