# PSX Technical Analyzer (Hardware-Aware Technical Analysis Application)

## Target Computer & System Specifications

This application is specifically designed and optimized for low-resource hardware:

* **OS:** Microsoft Windows 10 Home (x64)
* **CPU:** Intel Core i5-4210U @ 1.70 GHz (2 Cores, 4 Logical Processors)
* **RAM:** 8 GB Physical Memory (approx. 2–3 GB available during normal use)
* **Graphics:** CPU-first design. No GPU or CUDA required.
* **Virtualization:** No WSL2, Docker, or Hyper-V requirement.

---

## Hardware-Aware Software Architecture

To maintain high performance and responsiveness on dual-core CPU hardware with limited RAM:

1. **Lightweight & CPU-First:** Uses OpenCV, NumPy, and rule-based algorithms rather than heavy deep-learning frameworks.
2. **Sequential Image Pipeline:** Images are processed one by one (`Original -> Quality Check -> Thumbnail -> Region Cropping -> OCR/CV -> Numerical Validation -> Report Generation`) to conserve memory.
3. **Memory Optimization:** Unused full-resolution images and OpenCV matrices are explicitly freed from memory after each step. Intermediate results are stored on disk / SQLite database.
4. **Performance Modes:**
   - **STANDARD / LIGHTWEIGHT MODE (Default):** Optimized for low RAM (8GB) and dual-core CPUs with deterministic, CPU-first algorithms.
   - **HIGH ACCURACY / ADVANCED MODE:** Modular interfaces allow plugging in GPU models or external cloud services without modifying core logic.
5. **Graceful Degradation:** Low OCR confidence triggers manual data editing mode or marks fields as `"Not reliably extracted"` rather than failing.
6. **Diagnostic Monitoring:** Built-in resource overlay displays real-time CPU %, RAM usage, and stage execution timings.
