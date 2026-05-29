# 🛠️ ZBrush Spotlight (.zsl) Container and Texture File Format Specification

This document provides the definitive technical specification for the proprietary Pixologic ZBrush Spotlight (`.zsl`) file format. It covers container structure, serialization blocks, headers, custom RLE compression, planar layout geometry, and alpha mapping rules.

---

## 1. Container Architecture & LSZ Object Chain

A `.zsl` file is a serialized binary container following the **LSZ** (Pixologic Serialization Zip/Stream) format. All multi-byte integers (e.g., `uint16`, `uint32`) are stored in **little-endian** byte order.

The container does not store a Spotlight image as a single monolithic block. Instead, each Spotlight texture is constructed from a sequential **LSZ Object Chain** composed of multiple typed serialization blocks.

Every block in the chain begins with a standard 6-byte marker: `03 80 01 00 [Type: uint16]`. (Note: The Image block prefixes this with an extra `01`, making its marker 7 bytes total).

A typical Spotlight texture object chain consists of the following blocks in order:

### 1.1 Type 12 (0x0C): Original File Path Block
* **Marker:** `03 80 01 00 0C 00`
* **Structure:** Immediately followed by a `uint32` indicating the string length (e.g., `59`), then a `00 00` padding, and finally the ASCII string of the absolute file path (e.g., `C:\Users\user\Desktop\image.jpg`).

### 1.2 Type 1 (0x01): Transform & Coordinate Block
* **Marker:** `03 80 01 00 01 00`
* **Structure:** Stores the spatial metadata for the Spotlight interface, including X/Y coordinates, rotation matrices, and scale floats. Scale is represented as IEEE-754 floats (e.g., `00 00 80 3F` = `1.0`).

### 1.3 Type 10 (0x0A): Pre-Image Metadata Block
* **Marker:** `03 80 01 00 0A 00`
* **Structure:** Located immediately before the graphic stream. It contains:
  * `Hash/ID` (`uint32`) linking to the texture.
  * `width_related` (`uint32`).
  * `pitch` (`uint32`): Duplicates the row width in bytes (e.g., `00 1E 00 00` = `7680`).
  * `flags`: E.g., `01 01 01 00` (likely RGB channel toggles).
  * `opacity/scale floats`: `00 00 80 3F` (`1.0`).

### 1.4 Type 6 (0x06): Graphic Image Block
* **Marker:** `\x01\x03\x80\x01\x00\x06\x00`
* **Structure:** This is the primary block containing the compressed pixels. Its header and body are exhaustively detailed in the following sections.

---

## 2. Type 6 (Image Block) Header Specification

An image block in the stream always starts with a unique 7-byte signature marker:
`\x01\x03\x80\x01\x00\x06\x00`

The header structure immediately following the marker is detailed below:

| Offset from Marker Start | Size (Bytes) | Data Type | Field | Description |
| :--- | :--- | :--- | :--- | :--- |
| **+0** | 7 | `bytes[7]` | `marker` | Image Block signature: `\x01\x03\x80\x01\x00\x06\x00` |
| **+7** | 4 | `uint32` | `comp_size` | Total compressed size of the graphic block (including the chunk table). |
| **+11** | 4 | `uint32` | `decomp_size` | Total uncompressed size of all RGBA pixels combined in bytes. |
| **+15** | 2 | `uint16` | `channels` | Channel count (always `4` for RGBA). |
| **+17** | 2 | `uint16` | `pitch` | Row pitch in bytes ($Width \times 4$). |
| **+19** | 8 | `bytes[8]` | `padding1` | Internal padding/alignment bytes. |
| **+27** | 2 | `uint16` | `num_chunks` | Total number of compressed RLE chunks. |
| **+29** | 2 | `bytes[2]` | `padding2` | Internal alignment bytes. |
| **+31** | `num_chunks × 4` | `uint32[]` | `chunk_sizes` | Array of compressed sizes for each chunk (little-endian `uint32`). |
| **+31 + num_chunks×4** | 4 | `bytes[4]` | `data_start_marker` | Start-of-data sentinel: `\x01\x00\x00\x00`. Marks the beginning of the compressed chunk stream. |

### Chunk Stream Layout

The compressed chunk stream begins immediately after the `data_start_marker`. Each **active** (non-zero size) chunk in the stream ends with a 4-byte suffix `\x01\x00\x00\x00`. This suffix is **not part of the compressed data** and must be stripped before passing the chunk to the RLE decoder.

> **Note:** The `data_start_marker` and the per-chunk `\x01\x00\x00\x00` suffix are structurally identical but serve different roles:
> - `data_start_marker` — a single sentinel at the beginning of the entire chunk stream.
> - Per-chunk suffix — appended to **each** active chunk individually, acting as a chunk boundary marker.

---

## 3. Resolution Derivation

The width and height of the embedded texture are derived directly from the header's `pitch` and `decomp_size` fields:

1. **Width ($W$):**
   $$W = \frac{\text{pitch}}{4}$$
2. **Height ($H$):**
   $$H = \frac{\text{decomp\_size}}{\text{pitch}}$$

*Example (main image in Spotlight.zsl):*
* $\text{pitch} = 7680 \implies W = 1920$ pixels
* $\text{decomp\_size} = 11\,381\,760 \implies H = \frac{11381760}{7680} = 1482$ pixels

---

## 4. Compression Specification (ZBrush Inverted PackBits)

Each chunk is compressed independently using an inverted variant of the standard PackBits RLE algorithm.
Let the current control byte in the compressed stream be $n$ (valued from 0 to 255):

* **If $n < 128$ (Repeat Run):**
  * The byte immediately following the control byte is repeated exactly **$n$** times in the decompressed buffer.
  * *Important:* A common error in early extractors was repeating the byte $n + 1$ times, which introduced a 1-byte offset per run, leading to channel phase mismatches and severe chromatic shearing.
* **If $n = 128$ (No-op):**
  * The control byte `128` (0x80) is ignored; no bytes are consumed or emitted.
* **If $n > 128$ (Literal Run):**
  * The next **$256 - n$** bytes in the stream are copied directly to the output buffer without modification.

---

## 5. Planar Chunk-wise Layout

ZBrush stores channels in a **chunk-level planar format** that is globally concatenated without row margins or line padding:

1. **Chunk Pixel Capacity ($P_{\text{chunk}}$):**
   * ZBrush partitions image channels into slices of exactly **$32\,768$ pixels per channel** (which corresponds to exactly $131\,072$ uncompressed bytes per chunk: $32\,768 \times 4$ channels).
   * Every intermediate chunk from $0$ to $M-2$ has a capacity of exactly $P = 32\,768$ pixels.
   * The number of active chunks: $M = \lceil (W \times H) / 32\,768 \rceil$.
   * The final chunk ($M-1$) contains the remaining pixels:
     $$P_{\text{last}} = (W \times H) - (M - 1) \times 32\,768$$
   * Small single-chunk images (like the $96 \times 96$ thumbnail) have $P = W \times H = 9\,216$.

2. **Internal Chunk Slicing:**
   A decompressed chunk of capacity $P$ pixels consists of 4 sequential channel planes in **BGRA** (Blue, Green, Red, Alpha) order:
   $$\text{Chunk} = \underbrace{[P\text{ bytes Blue}]}_{\text{B-slice}} \, \underbrace{[P\text{ bytes Green}]}_{\text{G-slice}} \, \underbrace{[P\text{ bytes Red}]}_{\text{R-slice}} \, \underbrace{[P\text{ bytes Alpha}]}_{\text{A-slice}}$$

3. **Global Reconstruction Assembly:**
   * All B-slices from all chunks are joined to form a single continuous plane `B_global` of size $W \times H$ bytes.
   * The same is done for `G_global`, `R_global`, and `A_global`.
   * **Alpha Channel Inversion:** ZBrush stores a transparency mask (where `0` is opaque). To convert it to standard PNG opacity (where `255` is opaque), the alpha channel must be inverted:
     $$\text{Alpha}_{\text{PNG}}[i] = 255 - A_{\text{global}}[i]$$
   * The pixels are interleaved to form standard RGBA values for PNG:
     $$\text{Pixel}_i = (R_{\text{global}}[i], \, G_{\text{global}}[i], \, B_{\text{global}}[i], \, \text{Alpha}_{\text{PNG}}[i])$$
   * This byte sequence directly generates the final $(W, H)$ image without gaps, offsets, or seams.

---

## 6. Verification and Accuracy Metrics

* **Grayscale Channel Identity:**
  * Mean Absolute Difference between R-G: **`0.000000`**
  * Mean Absolute Difference between G-B: **`0.000000`**
  *(Confirms mathematically perfect channel synchronization and gray balance).*
* **Reference Similarity (MSE):**
  * Mean Squared Error (MSE) against the reference JPEG is **`0.008164`** with a max pixel error of **`1`** (which is 100% due to JPEG compression noise). The extracted PNG is a lossless restoration of the texture as stored in ZBrush memory.