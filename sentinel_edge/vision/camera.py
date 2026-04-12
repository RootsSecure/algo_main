import time
import logging
import numpy as np
import cv2

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False
    logging.warning("Picamera2 not available. Falling back to OpenCV video capture for development.")

class DualStreamCamera:
    """
    Handles Picamera2 dual-stream to output a 320x320 feed for YOLO
    and a 1080p feed for visual proof without scaling overhead.
    """
    def __init__(self):
        self.picam2 = None
        self.mock_cap = None
        self.is_hardware = PICAMERA_AVAILABLE

        if self.is_hardware:
            try:
                self.picam2 = Picamera2()
                config = self.picam2.create_preview_configuration(
                    main={"size": (1920, 1080), "format": "RGB888"},
                    lores={"size": (320, 320), "format": "RGB888"}
                )
                self.picam2.configure(config)
                self.picam2.start()
                time.sleep(2) # Give sensor time to auto-adjust exposure
                logging.info("Picamera2 dual-stream initialized.")
            except Exception as e:
                logging.error(f"Failed to initialize Picamera2 hardware: {e}")
                self.is_hardware = False
                
        if not self.is_hardware:
            self.mock_cap = cv2.VideoCapture(0)
            self.mock_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.mock_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            logging.info("OpenCV camera fallback initialized.")

    def capture_frame_pair(self):
        """
        Returns a tuple of numpy arrays: (lores_320x320_rgb, hires_1080p_rgb)
        """
        if self.is_hardware:
            req = self.picam2.capture_request()
            try:
                lores = req.make_array("lores")
                main = req.make_array("main")
                return lores, main
            finally:
                req.release()
        else:
            ret, frame = self.mock_cap.read()
            if not ret:
                # Return empty black arrays safely if drop occurs
                return np.zeros((320, 320, 3), dtype=np.uint8), np.zeros((1080, 1920, 3), dtype=np.uint8)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            lores = cv2.resize(frame_rgb, (320, 320))
            return lores, frame_rgb

    def save_visual_proof(self, hires_frame, output_path):
        """
        Saves the 1080p RGB array to disk as a BGR image.
        """
        bgr_frame = cv2.cvtColor(hires_frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, bgr_frame)
        logging.info(f"Visual proof preserved to {output_path}")
        return output_path

    def close(self):
        if self.is_hardware and self.picam2:
            self.picam2.stop()
            self.picam2.close()
        elif not self.is_hardware and self.mock_cap:
            self.mock_cap.release()
