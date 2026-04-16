import logging
import cv2
import numpy as np
try:
    import ncnn
except ImportError:
    logging.warning("NCNN library missing. Using mock inferencer.")
    ncnn = None

class MotionGate:
    """Blocks expensive inference until pixels cross a ratio threshold."""
    def __init__(self, threshold_ratio=0.05):
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=50, detectShadows=False)
        self.threshold_ratio = threshold_ratio

    def has_motion(self, frame_rgb):
        gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
        fg_mask = self.bg_subtractor.apply(gray)
        
        motion_pixels = cv2.countNonZero(fg_mask)
        total_pixels = frame_rgb.shape[0] * frame_rgb.shape[1]
        
        ratio = motion_pixels / total_pixels
        return ratio >= self.threshold_ratio, ratio

class NCNNYoloInferencer:
    """Wrapper for INT8-quantized YOLO26n using NCNN"""
    def __init__(self, bin_path, param_path, use_vulkan=True, conf_threshold=0.3):
        self.conf_threshold = conf_threshold
        self.target_size = 320
        self.is_mock = ncnn is None

        if not self.is_mock:
            import os
            if not os.path.exists(bin_path) or not os.path.exists(param_path):
                logging.warning(f"Model files {bin_path} or {param_path} not found. Using mock inferencer.")
                self.is_mock = True
            else:
                self.net = ncnn.Net()
                # Opt for Vulkan GPU acceleration where valid
                self.net.opt.use_vulkan_compute = use_vulkan
                try:
                    ret_param = self.net.load_param(param_path)
                    ret_bin = self.net.load_model(bin_path)
                    if ret_param != 0 or ret_bin != 0:
                        logging.error(f"Failed to load NCNN model paths (status P:{ret_param} B:{ret_bin})")
                        self.is_mock = True
                    else:
                        logging.info(f"NCNN YOLO model bound (Vulkan: {use_vulkan}).")
                except Exception as e:
                    logging.error(f"Failed to load NCNN model: {e}")
                    self.is_mock = True

    def detect(self, img_rgb):
        if self.is_mock:
            # Mock structure
            return []
            
        # Convert RGB numpy to normalized NCNN Mat
        mat_in = ncnn.Mat.from_pixels_resize(
            img_rgb, 
            ncnn.Mat.PixelType.PIXEL_RGB, 
            img_rgb.shape[1], 
            img_rgb.shape[0], 
            self.target_size, 
            self.target_size
        )

        mean_vals = [0.0, 0.0, 0.0]
        norm_vals = [1/255.0, 1/255.0, 1/255.0]
        mat_in.substract_mean_normalize(mean_vals, norm_vals)

        try:
            ex = self.net.create_extractor()
            ex.input("in0", mat_in)
            
            # Predict (typical output blob is 'out0')
            ret, mat_out = ex.extract("out0")
            if ret != 0:
                 return []
                 
            results = []
            # NCNN's custom output format: row = [label, prob, x1, y1, x2, y2]
            for i in range(mat_out.h):
                row = mat_out.row(i)
                conf = float(row[1])
                if conf < self.conf_threshold:
                    continue
                    
                label = int(row[0])
                
                # NCNN often emits standardized coordinates (0..1)
                x = float(row[2]) * self.target_size
                y = float(row[3]) * self.target_size
                w = (float(row[4]) - float(row[2])) * self.target_size
                h = (float(row[5]) - float(row[3])) * self.target_size
                
                results.append({
                    "class": label,
                    "conf": conf,
                    "bbox": [x, y, w, h]
                })
            return results
            
        except Exception as e:
            logging.error(f"Inference error execution: {e}")
            return []
