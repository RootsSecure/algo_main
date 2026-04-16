# Compiling the C++ Hybrid Vision Core

Because `sentinel_edge` relies on hardware-accelerated computer vision (Vulkan, V4L2, and NEON architectures) to conserve CPU cycles on the Raspberry Pi 4, the Vision framework must be compiled natively on the device instead of being installed via `piwheels`.

## Requirements

You must install the compilation toolchain to your Pi OS before proceeding:

```bash
sudo apt update
sudo apt install -y build-essential cmake git libgomp1
sudo apt install -y python3-dev python3-pybind11 \
                    libvulkan-dev vulkan-utils \
                    libopencv-dev 
```

*(Ensure you have at least 1GB of free RAM before compiling to prevent GCC from Out-Of-Memory crashing, or create a swapfile).*

## Step 1: Building NCNN

NCNN is the neural network framework that runs our `.bin` and `.param` models. It must be built locally to guarantee it is optimized for your Pi's exact ARM core variant.

```bash
cd ~
git clone -b 20231027 https://github.com/Tencent/ncnn.git
cd ncnn
git submodule update --init

mkdir build && cd build
# Compile with Vulkan Support enabled
cmake -DCMAKE_BUILD_TYPE=Release \
      -DNCNN_VULKAN=ON \
      -DNCNN_BUILD_EXAMPLES=OFF \
      -DNCNN_BUILD_TOOLS=OFF \
      ..
      
make -j4
sudo make install
```

## Step 2: Compiling the Pybind11 `sentinel_vision.so`

Now that NCNN is globally accessible, we can compile our custom `vision_bindings.cpp`:

```bash
# Move into the plot sentinel directory
cd ~/nri_plot_sentinel/sentinel_edge/vision_cpp/

# Create a build folder
mkdir build && cd build

# Map to the virtual environment specifically so Pybind links to the right Python paths
cmake -DPYTHON_EXECUTABLE=../../venv/bin/python ..

# Compile the core
make -j4
```

## Step 3: Verifying the Architecture

If compilation succeeded, `make` will automatically drop `sentinel_vision.cpython-...-arm-linux-gnueabihf.so` directly into the `sentinel_edge/core/` directory.

You can verify it by activating your virtual environment and testing the import:
```bash
cd ../../
source venv/bin/activate

python -c "import core.sentinel_vision; print('C++ Hybrid Load Success!')"
```
