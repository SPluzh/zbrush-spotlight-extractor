"""
zbrush-spotlight-extractor — extracts embedded textures from ZBrush Spotlight (.zsl) files
and saves them as RGBA PNG images.

Usage:
    python zsltoimg.py <path_to_file.zsl>

Output is placed in a folder named <filename>_extracted next to the source file.
"""

import os
import sys
import struct
import zlib
import zslformat


def write_png(path: str, width: int, height: int, rgba_data: bytes) -> None:
    """
    Saves raw RGBA pixel data to a standard PNG file using only built-in modules
    (zlib, struct) to avoid external dependencies like Pillow.
    """
    png_sig = b'\x89PNG\r\n\x1a\n'
    
    def make_chunk(tag: bytes, data: bytes) -> bytes:
        length = struct.pack('>I', len(data))
        crc = struct.pack('>I', zlib.crc32(tag + data))
        return length + tag + data + crc

    # IHDR: width, height, 8-bit depth, color type 6 (RGBA), compression 0, filter 0, interlace 0
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = make_chunk(b'IHDR', ihdr_data)

    # IDAT: Scanlines prefixed with filter type 0 (None)
    row_size = width * 4
    filtered_data = bytearray()
    for y in range(height):
        filtered_data.append(0)
        filtered_data.extend(rgba_data[y * row_size : (y + 1) * row_size])
        
    idat = make_chunk(b'IDAT', zlib.compress(bytes(filtered_data), level=9))
    iend = make_chunk(b'IEND', b'')

    with open(path, 'wb') as f:
        f.write(png_sig + ihdr + idat + iend)


def extract(zsl_path: str, output_dir: str) -> bool:
    """
    Reads *zsl_path*, extracts all embedded image blocks, and saves
    each one as a PNG file inside *output_dir*.

    Returns True if at least one image was saved successfully.
    """
    if not os.path.exists(zsl_path):
        print(f"Error: file not found: '{zsl_path}'")
        return False

    print(f"Reading '{zsl_path}'...")
    with open(zsl_path, 'rb') as f:
        data = f.read()

    offsets = zslformat.find_image_blocks(data)
    if not offsets:
        print("No embedded image blocks found.")
        return False

    print(f"Found {len(offsets)} image block(s).")
    os.makedirs(output_dir, exist_ok=True)

    saved = 0
    total = len(offsets)

    for i, offset in enumerate(offsets):
        header = zslformat.parse_block_header(data, offset)
        width, height = header['width'], header['height']

        chunks     = zslformat.decompress_block(data, header)
        pixel_data = zslformat.assemble_rgba(chunks, width, height)

        # Resolve output filename
        src_name = zslformat.find_source_filename(data, offset)
        if src_name:
            out_name = os.path.splitext(src_name)[0] + '.png'
        elif i == 0:
            out_name = 'thumbnail.png'
        else:
            out_name = f'extracted_image_{i}.png'

        out_path = os.path.join(output_dir, out_name)

        try:
            write_png(out_path, width, height, pixel_data)
            print(f"  [{i+1}/{total}] {out_name}  ({width}x{height})")
            saved += 1
        except Exception as exc:
            print(f"  [{i+1}/{total}] Error saving block {i}: {exc}")

    print(f"\nDone. Saved {saved}/{total} image(s) -> {output_dir}")
    return saved > 0



def main():
    if len(sys.argv) > 1:
        zsl_file = os.path.abspath(sys.argv[1])
    else:
        # Fallback: look for Spotlight.zsl next to the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        zsl_file = os.path.join(script_dir, 'Spotlight.zsl')
        if not os.path.exists(zsl_file):
            print("Usage: python zsltoimg.py <path_to_file.zsl>")
            sys.exit(1)

    zsl_dir  = os.path.dirname(zsl_file)
    zsl_base = os.path.splitext(os.path.basename(zsl_file))[0]
    out_dir  = os.path.join(zsl_dir, f"{zsl_base}_extracted")

    sys.exit(0 if extract(zsl_file, out_dir) else 1)


if __name__ == "__main__":
    main()