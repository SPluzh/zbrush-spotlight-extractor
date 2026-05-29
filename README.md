# zbrush-spotlight-extractor

A Python tool for extracting embedded textures from ZBrush Spotlight (`.zsl`) files and saving them as standard PNG images.

---

## What is a .zsl file?

ZBrush Spotlight is a texture management system built into ZBrush. When a Spotlight session is saved, ZBrush serializes all loaded textures into a proprietary binary container with a `.zsl` extension. Each texture is stored in a compressed, planar-channel format — not as a standard image file — making it inaccessible to ordinary image viewers or converters.

**zbrush-spotlight-extractor** reverse-engineers this format and reconstructs pixel-perfect PNG images from the raw binary data.

---

## Features

- Finds all embedded image blocks in the `.zsl` container
- Decompresses ZBrush's inverted PackBits RLE format
- Reconstructs full RGBA images from chunk-level BGRA planar data
- Recovers original source filenames from container metadata
- Saves PNGs into `<filename>_extracted/` next to the input file
- Windows drag-and-drop batch script included

---

## Project Structure

```
zslformat.py            # Format library: RLE decoder, block parser, channel assembler
zsltoimg.py             # CLI entry point: file I/O, PNG saving, progress output
zsltoimg.bat            # Windows drag-and-drop launcher
zsl_specification.md    # Full technical specification of the .zsl format
```

---

## Usage

### Easy Way: Pre-compiled Executable (Windows)

The easiest way to use the tool is to download the standalone **`zsltoimg.exe`** from the [Releases](https://github.com/your-username/zbrush-spotlight-extractor/releases) page:

1. **Drag and Drop:** Simply drag any `.zsl` file from File Explorer and drop it onto `zsltoimg.exe`. It will automatically extract all textures into a folder next to the source file and show a completion log.
2. **Command Line:** Run the executable from your terminal:
   ```bash
   zsltoimg.exe <path_to_file.zsl>
   ```

### Developer Way: Python Script

If you prefer to run the raw source code, it requires **Python 3** and has **zero external dependencies**:

1. Run the script from the command line:
   ```bash
   python zsltoimg.py <path_to_file.zsl>
   ```
2. **Windows Drag-and-Drop Wrapper:** Alternatively, drag and drop any `.zsl` file onto `zsltoimg.bat` in the repository root.

---

## How It Works

### 1. Container Parsing

A `.zsl` file uses the LSZ (Pixologic Serialization) binary format. `zslformat.find_image_blocks()` scans the raw bytes for type `0x06` markers (`\x01\x03\x80\x01\x00\x06\x00`); `zslformat.parse_block_header()` extracts width, height, and chunk layout.

### 2. RLE Decompression

Each compressed chunk uses an inverted PackBits algorithm:

- Control byte `n < 128` → repeat the next byte exactly **n** times
- Control byte `n = 128` → no-op, skip
- Control byte `n > 128` → copy the next **256 − n** bytes literally

### 3. Planar Channel Reassembly

ZBrush stores pixel data in **chunk-level planar BGRA format**: each chunk holds 32 768 pixels split into four equal planes — Blue, Green, Red, Alpha — in that order. The tool:

1. Extracts B/G/R/A slices from every chunk
2. Concatenates all slices of the same channel into global planes
3. Inverts the alpha channel (`255 − value`) to convert ZBrush's transparency mask to standard PNG opacity
4. Interleaves the planes into RGBA pixel data and saves as PNG

For a detailed technical breakdown, see [`zsl_specification.md`](zsl_specification.md).

---

## License

MIT
