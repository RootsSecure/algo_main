#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <opencv2/opencv.hpp>
#include <net.h>
#include <thread>
#include <mutex>
#include <atomic>
#include <iostream>
#include <chrono>

namespace py = pybind11;

class HybridVisionCore {
private:
    cv::VideoCapture cap;
    cv::Ptr<cv::BackgroundSubtractorMOG2> bg_subtractor;
    cv::Mat latest_frame;
    std::mutex frame_mutex;
    std::atomic<bool> running;
    std::thread capture_thread;

    ncnn::Net yolov_net;
    bool model_loaded;

    void capture_loop() {
        cv::Mat frame;
        while (running) {
            // Read from V4L2 backend asynchronously
            if (cap.read(frame)) {
                std::lock_guard<std::mutex> lock(frame_mutex);
                frame.copyTo(latest_frame);
            } else {
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
        }
    }

public:
    HybridVisionCore(const std::string& bin_path, const std::string& param_path) 
        : running(false), model_loaded(false) {
        
        bg_subtractor = cv::createBackgroundSubtractorMOG2(100, 50, false);
        
        // Fast paths for Raspberry Pi 4 ARMv8 architecture
        yolov_net.opt.use_vulkan_compute = true;
        yolov_net.opt.num_threads = 4;

        if (yolov_net.load_param(param_path.c_str()) == 0 && yolov_net.load_model(bin_path.c_str()) == 0) {
            model_loaded = true;
            std::cout << "[CPP] NCNN Model loaded successfully." << std::endl;
        } else {
            std::cerr << "[CPP] Failed to load NCNN Model paths. Expecting Mock behavior." << std::endl;
        }
    }

    ~HybridVisionCore() {
        stop_camera();
    }

    bool start_camera(int device_id = 0, int width = 1920, int height = 1080) {
        // Force V4L2 block on Raspberry Pi bounds
        cap.open(device_id, cv::CAP_V4L2);
        if (!cap.isOpened()) {
            std::cerr << "[CPP] Failed to open V4L2 camera block." << std::endl;
            return false;
        }
        cap.set(cv::CAP_PROP_FRAME_WIDTH, width);
        cap.set(cv::CAP_PROP_FRAME_HEIGHT, height);
        
        running = true;
        capture_thread = std::thread(&HybridVisionCore::capture_loop, this);
        std::this_thread::sleep_for(std::chrono::milliseconds(500)); // warmup
        return true;
    }

    void stop_camera() {
        running = false;
        if (capture_thread.joinable()) {
            capture_thread.join();
        }
        if (cap.isOpened()) {
            cap.release();
        }
    }

    py::dict process_frame(float threshold_ratio = 0.05) {
        cv::Mat current;
        {
            std::lock_guard<std::mutex> lock(frame_mutex);
            if (latest_frame.empty()) {
                py::dict result;
                result["has_motion"] = false;
                result["detections"] = py::list();
                return result;
            }
            latest_frame.copyTo(current);
        }

        py::dict result;
        
        // 1. C++ MOG2 Motion Gate bypass Python totally
        cv::Mat gray, fg_mask;
        cv::cvtColor(current, gray, cv::COLOR_BGR2GRAY);
        bg_subtractor->apply(gray, fg_mask);
        
        int motion_pixels = cv::countNonZero(fg_mask);
        int total_pixels = current.rows * current.cols;
        float ratio = (float)motion_pixels / total_pixels;
        
        bool has_motion = (ratio >= threshold_ratio);
        result["has_motion"] = has_motion;
        result["motion_ratio"] = ratio;
        
        py::list py_detections;
        result["detections"] = py_detections;

        if (!has_motion || !model_loaded) {
            return result;
        }

        // 2. C++ Native INT8 Inference
        int target_size = 320;
        ncnn::Mat mat_in = ncnn::Mat::from_pixels_resize(
            current.data, 
            ncnn::Mat::PIXEL_BGR2RGB, 
            current.cols, current.rows, 
            target_size, target_size
        );

        const float mean_vals[3] = {0.f, 0.f, 0.f};
        const float norm_vals[3] = {1/255.f, 1/255.f, 1/255.f};
        mat_in.substract_mean_normalize(mean_vals, norm_vals);

        ncnn::Extractor ex = yolov_net.create_extractor();
        ex.input("in0", mat_in);

        ncnn::Mat mat_out;
        ex.extract("out0", mat_out);

        for (int i = 0; i < mat_out.h; i++) {
            const float* values = mat_out.row(i);
            float conf = values[1];
            if (conf < 0.3f) continue;
            
            py::dict det;
            det["class"] = (int)values[0];
            det["conf"] = conf;
            
            // Standard bounding boxes parsed onto Python arrays directly
            float x = values[2] * target_size;
            float y = values[3] * target_size;
            float w = (values[4] - values[2]) * target_size;
            float h = (values[5] - values[3]) * target_size;
            
            py::list bbox;
            bbox.append(x); bbox.append(y); bbox.append(w); bbox.append(h);
            det["bbox"] = bbox;
            
            py_detections.append(det);
        }
        
        result["detections"] = py_detections;
        return result;
    }

    bool save_visual_proof(const std::string& path) {
        cv::Mat current;
        {
            std::lock_guard<std::mutex> lock(frame_mutex);
            if (latest_frame.empty()) return false;
            latest_frame.copyTo(current);
        }
        // OpenCV natively interprets matrices as BGR, so it writes correctly
        return cv::imwrite(path, current);
    }
};

PYBIND11_MODULE(sentinel_vision, m) {
    m.doc() = "Hybrid C++ Vision Core with NCNN and Pybind11";

    py::class_<HybridVisionCore>(m, "HybridVisionCore")
        .def(py::init<const std::string&, const std::string&>())
        .def("start_camera", &HybridVisionCore::start_camera, py::arg("device_id") = 0, py::arg("width") = 1920, py::arg("height") = 1080)
        .def("stop_camera", &HybridVisionCore::stop_camera)
        .def("process_frame", &HybridVisionCore::process_frame, py::arg("threshold_ratio") = 0.05)
        .def("save_visual_proof", &HybridVisionCore::save_visual_proof);
}
