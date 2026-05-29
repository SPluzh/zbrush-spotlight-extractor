"""
zbrush-spotlight-extractor — extracts embedded textures from ZBrush Spotlight (.zsl) files
and saves them as RGBA PNG images.

Usage:
    python zsltoimg.py <path_to_file.zsl>

Output is placed in a folder named <filename>_extracted next to the source file.
"""

import os
import sys

from PIL import Image
import zslformat


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
            img = Image.frombytes('RGBA', (width, height), pixel_data)
            img.save(out_path)
            print(f"  [{i+1}/{total}] {out_name}  ({width}×{height})")
            saved += 1
        except Exception as exc:
            print(f"  [{i+1}/{total}] Error saving block {i}: {exc}")

    print(f"\nDone. Saved {saved}/{total} image(s) → {output_dir}")
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