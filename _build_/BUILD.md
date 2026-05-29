# Compiling zsltoimg into a Standalone EXE in `_build_`

**PyInstaller** is used to compile the Python CLI script into a single, independent executable `.exe` file. The repository already includes the complete build pipeline inside the `_build_` directory.

> [!NOTE]
> All build scripts are pre-configured to run on Windows from the `_build_` folder in a single click.

---

## Build Plan

1. **Install Dependencies**
   The extractor is developed with **zero external dependencies** (to maintain the absolute minimum file size, Pillow was completely replaced by a custom pure-Python PNG writer!). You only need `PyInstaller` to build the executable.
   ```bash
   pip install pyinstaller
   ```

2. **Compiler Configuration (`_build_\zsltoimg.spec`)**
   We have prepared a highly optimized PyInstaller specification file with precise compilation rules:
   * **Single File (`--onefile`)**: Packages all dependencies into a single, compact EXE.
   * **Console Mode (`console=True`)**: Keeps the console window open to display extraction logs and support drag-and-drop operations.
   * **Aggressive Excludes (`excludes`)**: Excludes heavy unused standard Python libraries (such as networking, async frameworks, XML parsing, database connectors, and archive compression modules), saving over 20 MB of distribution size.

3. **Build Automation Script (`_build_\__build.bat`)**
   To make building a single-click process while achieving extreme binary compression, we created the `__build.bat` script. It automates the following steps:
   * **Environment Check**: Confirms that Python and PyInstaller are accessible via the system `PATH`.
   * **Clean Previous Builds**: Deletes temporary artifacts (`build/`, `dist/`, and older `zsltoimg.exe`) to prevent caching conflicts.
   * **Code Size Optimization**: Compiles the script using Python's maximum optimization flag **`-OO`** (`python -OO -m PyInstaller zsltoimg.spec`), stripping all docstrings and `assert` statements from compiled bytecode.
   * **Result Processing**: Moves the generated `zsltoimg.exe` from the temporary `dist/` directory directly into the `_build_` root directory.
   * **Cleanup**: Deletes temporary build directories.
   * **Post-compilation UPX Ultra-Compression**: Runs `upx.exe --ultra-brute --force zsltoimg.exe` to perform deep dictionary-based compression on the final binary, squeezing it to the absolute minimum physical size.
   * **Display Output**: Automatically opens the output directory in Windows Explorer.

---

## How to Build

1. Open the `_build_` directory.
2. Double-click the `__build.bat` file (or execute it via terminal).
3. Wait for the compilation and UPX compression to complete.
4. The standalone executable **`zsltoimg.exe`** will appear in the `_build_` folder.

> [!TIP]
> **How to Use the Compiled EXE:**
> Simply drag any `.zsl` file (ZBrush Spotlight) from File Explorer and drop it onto `zsltoimg.exe`. The utility will automatically create a `<filename>_extracted` folder next to the source file and extract all embedded textures as standard PNG images.
