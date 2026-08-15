# Hardware and Architecture Constraints

## Target Hardware Specifications

- **OS**: Windows 10 Home (64-bit)
- **CPU**: Intel Core i5-4210U (Dual Core, 1.70 GHz – 2.40 GHz)
- **RAM**: 8 GB Total (~2–3 GB available during execution)
- **GPU**: None (CPU-first execution only; strictly no CUDA or heavy GPU dependencies)

## Software Architecture Requirements

1. **Lightweight Library Stack**:
   - **GUI**: PySide6
   - **Image Processing**: OpenCV (`opencv-python-headless` / `opencv-python`) & Pillow
   - **Data Processing & Analysis**: Pandas / NumPy
   - **Database**: SQLite (built-in `sqlite3`)

2. **Strict Memory & Dependency Limits**:
   - No heavy local AI/ML frameworks (strictly no PyTorch, TensorFlow, or large multimodal models).
   - CPU-bound computations designed for dual-core, low-power operation.

3. **Sequential Image Processing**:
   - Process **1 image at a time** in pipelines to prevent RAM spikes and ensure stability within 2–3 GB available RAM constraints.

4. **Two-Tier Mode Design**:
   - **Standard / Lightweight Mode**: Default execution mode tailored for low-resource hardware (Intel i5-4210U / 8GB RAM).
   - **Advanced Mode**: Modular placeholder system for future hardware upgrades or expanded compute capacity.

5. **Standalone Distribution**:
   - Designed and organized to be seamlessly packaged into a standalone `.exe` using **PyInstaller**.
