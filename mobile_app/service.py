import time
from oscpy.client import OSCClient
from communication_manager import CommunicationManager

class BackgroundAlertHandler:
    """
    Dummy handler mirroring Kivy's AlertHandler logic specifically for the background process.
    Receives JSON strings from CommunicationManager and pipes them to the active Kivy UI over OSC.
    """
    def __init__(self):
        # Bind to 3000 which the Kivy foreground app listens to
        self.osc = OSCClient("localhost", 3000)

    def receive_heartbeat(self):
        # Forward heartbeat pulse to Kivy foreground
        self.osc.send_message(b'/heartbeat', [])
        
    def handle_incoming_alert(self, payload):
        # Forward the raw JSON string over OSC
        self.osc.send_message(b'/alert', [payload.encode('utf-8')])

if __name__ == '__main__':
    print("[RootsSecure Background] Service Started.")
    
    # OS Level Service Instantiation
    # Initialize connection to MQTT broker
    # E.g., 'test.mosquitto.org' for MVP, swap with production IP for edge router deployment
    broker_address = "broker.hivemq.com"
    
    handler = BackgroundAlertHandler()
    manager = CommunicationManager(broker_address, alert_handler=handler)
    manager.start()
    
    # Process keeps running indefinitely mimicking OS daemons
    while True:
        # Keep process alive whilst daemon thread manages MQTT loops
        time.sleep(1)
