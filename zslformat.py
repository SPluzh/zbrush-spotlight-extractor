"""
zslformat — ZBrush Spotlight (.zsl) format parser.

See zsl_specification.md for the full format specification.
"""

import struct
from itertools import chain

# ── Constants ────────────────────────────────────────────────────────────────

# 7-byte signature of a Type-6 (Graphic Image) block.
IMAGE_BLOCK_MARKER = b'\x01\x03\x80\x01\x00\x06\x00'

# Uncompressed pixels per channel per intermediate chunk (32 768).
CHUNK_PIXELS = 32_768

# Per-chunk stream suffix that must be stripped before RLE decoding.
CHUNK_SUFFIX = b'\x01\x00\x00\x00'

# ── RLE decoder ──────────────────────────────────────────────────────────────

def decode_rle(data: bytes) -> bytes:
    """
    Decodes a ZBrush inverted PackBits RLE stream.

    Control byte n:
      n < 128  — repeat run:  repeat the next byte exactly n times.
      n = 128  — no-op:       skip (nothing emitted).
      n > 128  — literal run: copy the next (256 - n) bytes verbatim.
    """
    out = bytearray()
    i = 0
    while i < len(data):
        n = data[i]
        i += 1
        if n < 128:
            count = n
            if count == 0:
                continue
            if i < len(data):
                val = data[i]
                i += 1
                out.extend([val] * count)
            else:
                break
        elif n == 128:
            continue
        else:
            count = 256 - n
            if i + count <= len(data):
                out.extend(data[i : i + count])
                i += count
            else:
                out.extend(data[i:])
                break
    return bytes(out)

# ── Block discovery ──────────────────────────────────────────────────────────

def find_image_blocks(data: bytes) -> list:
    """
    Scans the raw .zsl bytes and returns a list of offsets of every
    Type-6 (Graphic Image) block marker.
    """
    offsets = []
    idx = 0
    while True:
        idx = data.find(IMAGE_BLOCK_MARKER, idx)
        if idx == -1:
            break
        offsets.append(idx)
        idx += 1
    return offsets

# ── Header parsing ───────────────────────────────────────────────────────────

def parse_block_header(data: bytes, offset: int) -> dict:
    """
    Parses a Type-6 image block header starting at *offset* (the position
    of the IMAGE_BLOCK_MARKER).

    Returns a dict with keys:
        width       (int)   — image width in pixels
        height      (int)   — image height in pixels
        pitch       (int)   — row width in bytes (width × 4)
        decomp_size (int)   — total uncompressed RGBA size in bytes
        chunk_sizes (tuple) — compressed size of each RLE chunk
        data_start  (int)   — absolute offset of the first chunk in *data*
    """
    marker_len = len(IMAGE_BLOCK_MARKER)
    hdr = offset + marker_len

    # +0  uint32  comp_size
    # +4  uint32  decomp_size
    # +8  uint16  channels
    # +10 uint16  pitch
    comp_size, decomp_size, channels, pitch = struct.unpack_from('<IIHH', data, hdr)

    # num_chunks sits at offset+27 (8 padding bytes after pitch)
    num_chunks = struct.unpack_from('<H', data, offset + 27)[0]

    # chunk_sizes table starts at offset+31
    table_offset = offset + 31
    chunk_sizes = struct.unpack_from('<' + 'I' * num_chunks, data, table_offset)

    # Compressed stream starts right after the table + 4-byte data_start_marker
    data_start = table_offset + num_chunks * 4 + 4

    width  = pitch // 4
    height = decomp_size // pitch if pitch else 0

    return {
        'width':       width,
        'height':      height,
        'pitch':       pitch,
        'decomp_size': decomp_size,
        'chunk_sizes': chunk_sizes,
        'data_start':  data_start,
    }

# ── Chunk decompression ──────────────────────────────────────────────────────

def decompress_block(data: bytes, header: dict) -> list:
    """
    Reads and RLE-decompresses all active chunks described by *header*.

    Returns a list of decompressed chunk bytes (skipping zero-size chunks).
    """
    chunks = []
    cursor = header['data_start']
    for c_size in header['chunk_sizes']:
        if c_size == 0:
            continue
        raw = data[cursor : cursor + c_size]
        cursor += c_size
        if raw.endswith(CHUNK_SUFFIX):
            raw = raw[:-4]
        chunks.append(decode_rle(raw))
    return chunks

# ── RGBA assembly ─────────────────────────────────────────────────────────────

def assemble_rgba(chunks: list, width: int, height: int) -> bytes:
    """
    Assembles decompressed chunk-level BGRA planar data into a flat
    interleaved RGBA byte sequence suitable for PIL Image.frombytes('RGBA', …).

    ZBrush chunk layout per chunk of P pixels:
        [P bytes Blue][P bytes Green][P bytes Red][P bytes Alpha]

    Alpha is stored as a transparency mask (0 = opaque) and is inverted
    to standard PNG opacity (255 = opaque) during assembly.
    """
    total_pixels = width * height
    num_chunks   = len(chunks)

    b_slices, g_slices, r_slices, a_slices = [], [], [], []

    for i, chunk in enumerate(chunks):
        if num_chunks > 1:
            P = (total_pixels - (num_chunks - 1) * CHUNK_PIXELS
                 if i == num_chunks - 1
                 else CHUNK_PIXELS)
        else:
            P = total_pixels

        b_slices.append(chunk[0     : P])
        g_slices.append(chunk[P     : 2*P])
        r_slices.append(chunk[2*P   : 3*P])
        a_slices.append(chunk[3*P   : 4*P])

    r = b"".join(r_slices)
    g = b"".join(g_slices)
    b = b"".join(b_slices)
    a = bytes(255 - v for v in b"".join(a_slices))   # invert transparency→opacity

    return bytes(chain.from_iterable(zip(r, g, b, a)))

# ── Filename recovery ─────────────────────────────────────────────────────────

def find_source_filename(data: bytes, block_offset: int) -> str:
    """
    Searches up to 1000 bytes before *block_offset* for the original
    source filename stored in the Type-12 (File Path) block.

    Returns the bare filename (e.g. 'texture.jpg') or None if not found.
    Recognised extensions: .jpg, .jpeg, .png
    """
    search_limit = 1000
    start = max(0, block_offset - search_limit)
    window = data[start : block_offset]

    best_idx = -1
    best_ext_len = 4
    for ext in (b'.jpg', b'.jpeg', b'.png'):
        pos = window.rfind(ext)
        if pos > best_idx:
            best_idx = pos
            best_ext_len = len(ext)

    if best_idx == -1:
        return None

    end = best_idx + best_ext_len
    fn_start = end
    while fn_start > 0:
        ch = window[fn_start - 1]
        if ch in (0, ord('\\'), ord('/')):
            break
        fn_start -= 1

    return window[fn_start : end].decode('utf-8', errors='ignore') or None
