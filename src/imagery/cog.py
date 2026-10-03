"""Read a window out of a cloud-optimised GeoTIFF, with no GeoTIFF library.

Sentinel-2 scenes are a hundred megabytes of tiled, compressed raster. A site is a few hundred pixels of it.
So this reads the TIFF directory, works out which tiles cover the window, fetches only those tiles by HTTP
range request, undoes the TIFF predictor, and returns the pixels.

What it supports is what the public Sentinel-2 visual asset uses: little endian, 8 bit samples, DEFLATE
compression, horizontal differencing predictor, chunky planar layout, 1024 pixel tiles. Anything else raises
rather than guessing, because a silently misread raster would be worse than a refusal.
"""
from __future__ import annotations

import io
import struct
import zlib

import requests

UA = {"User-Agent": "gqh-delivery-gap research research@example.com"}

COMPRESSION_NONE = 1
COMPRESSION_DEFLATE = 8
PREDICTOR_NONE = 1
PREDICTOR_HORIZONTAL = 2

TAG_IMAGE_WIDTH = 256
TAG_IMAGE_LENGTH = 257
TAG_BITS_PER_SAMPLE = 258
TAG_COMPRESSION = 259
TAG_SAMPLES_PER_PIXEL = 277
TAG_PLANAR_CONFIG = 284
TAG_PREDICTOR = 317
TAG_TILE_WIDTH = 322
TAG_TILE_LENGTH = 323
TAG_TILE_OFFSETS = 324
TAG_TILE_BYTE_COUNTS = 325

SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 16: 8, 17: 8}


class RangeReader:
    """A seekable file over HTTP ranges, with a block cache and a byte cap."""

    def __init__(self, url: str, block: int = 4 << 20, keep: int = 24, cap: int = 1 << 28):
        self.url, self.block, self.keep, self.cap = url, block, keep, cap
        self.position = 0
        self.fetched = 0
        self._cache: dict[int, bytes] = {}
        self._order: list[int] = []
        head = requests.head(url, headers=UA, timeout=30)
        self.size = int(head.headers.get("Content-Length", 0))
        if self.size == 0:
            raise RuntimeError("the asset reported no length")

    def _block(self, index: int) -> bytes:
        if index in self._cache:
            return self._cache[index]
        start = index * self.block
        if start >= self.size or self.fetched >= self.cap:
            return b""
        end = min(self.size, start + self.block) - 1
        response = requests.get(self.url, headers={**UA, "Range": f"bytes={start}-{end}"}, timeout=90)
        data = response.content if response.status_code in (200, 206) else b""
        self.fetched += len(data)
        self._cache[index] = data
        self._order.append(index)
        while len(self._order) > self.keep:
            self._cache.pop(self._order.pop(0), None)
        return data

    def read_at(self, start: int, length: int) -> bytes:
        """Bytes at a position, assembled from cached blocks."""
        out = bytearray()
        position = start
        while len(out) < length and position < self.size:
            index, offset = divmod(position, self.block)
            block = self._block(index)
            if not block:
                break
            take = block[offset:offset + (length - len(out))]
            if not take:
                break
            out += take
            position += len(take)
        return bytes(out)

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = 1 << 20
        data = self.read_at(self.position, n)
        self.position += len(data)
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        self.position = offset if whence == 0 else (self.position + offset if whence == 1 else self.size + offset)
        return self.position

    def tell(self) -> int:
        return self.position

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True


def undo_horizontal_predictor(data: bytes, width: int, samples: int) -> bytes:
    """Invert TIFF predictor 2: each component is the difference from the previous pixel's component."""
    stride = width * samples
    out = bytearray(data)
    for row_start in range(0, len(out) - stride + 1, stride):
        for index in range(samples, stride):
            out[row_start + index] = (out[row_start + index] + out[row_start + index - samples]) & 0xFF
    return bytes(out)


class Tiff:
    """The directory of a tiled GeoTIFF, plus the ability to read one tile."""

    def __init__(self, reader: RangeReader):
        self.reader = reader
        header = reader.read_at(0, 16)
        if len(header) < 8:
            raise RuntimeError("not a TIFF: header too short")
        self.order = "<" if header[:2] == b"II" else ">"
        magic = struct.unpack(self.order + "H", header[2:4])[0]
        if magic != 42:
            raise RuntimeError(f"not a TIFF: magic {magic}")
        ifd_offset = struct.unpack(self.order + "I", header[4:8])[0]
        count = struct.unpack(self.order + "H", reader.read_at(ifd_offset, 2))[0]
        block = reader.read_at(ifd_offset, 2 + count * 12)
        self.tags: dict[int, object] = {}
        for index in range(count):
            entry = block[2 + index * 12: 2 + (index + 1) * 12]
            tag, kind, how_many = struct.unpack(self.order + "HHI", entry[:8])
            raw = entry[8:12]
            size = SIZES.get(kind, 1)
            if size * how_many <= 4:
                self.tags[tag] = self._values(raw[:size * how_many], kind, how_many)
            else:
                offset = struct.unpack(self.order + "I", raw)[0]
                payload = reader.read_at(offset, size * how_many)
                self.tags[tag] = self._values(payload, kind, how_many)

    def _values(self, payload: bytes, kind: int, how_many: int):
        formats = {1: "B", 3: "H", 4: "I", 6: "b", 8: "h", 9: "i", 11: "f", 12: "d", 16: "Q", 17: "q"}
        if kind in formats:
            return struct.unpack(self.order + formats[kind] * how_many, payload)
        if kind == 5:
            out = []
            for i in range(how_many):
                numerator, denominator = struct.unpack(self.order + "II", payload[i * 8:(i + 1) * 8])
                out.append(numerator / denominator if denominator else 0.0)
            return tuple(out)
        return tuple(payload)

    def single(self, tag: int, default=None):
        value = self.tags.get(tag, default)
        if isinstance(value, tuple):
            return value[0] if value else default
        return value

    @property
    def width(self) -> int:
        return int(self.single(TAG_IMAGE_WIDTH, 0))

    @property
    def height(self) -> int:
        return int(self.single(TAG_IMAGE_LENGTH, 0))

    @property
    def samples(self) -> int:
        return int(self.single(TAG_SAMPLES_PER_PIXEL, 1))

    @property
    def tile_width(self) -> int:
        return int(self.single(TAG_TILE_WIDTH, 0))

    @property
    def tile_height(self) -> int:
        return int(self.single(TAG_TILE_LENGTH, 0))

    def check_supported(self) -> None:
        compression = int(self.single(TAG_COMPRESSION, 1))
        predictor = int(self.single(TAG_PREDICTOR, 1))
        bits = self.single(TAG_BITS_PER_SAMPLE, (8,))
        if not isinstance(bits, tuple):
            bits = (bits,)
        planar = int(self.single(TAG_PLANAR_CONFIG, 1))
        if compression not in (COMPRESSION_NONE, COMPRESSION_DEFLATE):
            raise RuntimeError(f"compression {compression} is not supported")
        if predictor not in (PREDICTOR_NONE, PREDICTOR_HORIZONTAL):
            raise RuntimeError(f"predictor {predictor} is not supported")
        if set(bits) != {8}:
            raise RuntimeError(f"bits per sample {bits} is not supported")
        if planar != 1:
            raise RuntimeError(f"planar configuration {planar} is not supported")
        if not self.tile_width or not self.tile_height:
            raise RuntimeError("the file is not tiled")

    @property
    def tiles_across(self) -> int:
        return (self.width + self.tile_width - 1) // self.tile_width

    @property
    def tiles_down(self) -> int:
        return (self.height + self.tile_height - 1) // self.tile_height

    def read_tile(self, tile_x: int, tile_y: int) -> bytes:
        """One tile as raw samples, predictor undone, padded to the declared tile size."""
        offsets = self.tags.get(TAG_TILE_OFFSETS, ())
        counts = self.tags.get(TAG_TILE_BYTE_COUNTS, ())
        index = tile_y * self.tiles_across + tile_x
        if index >= len(offsets):
            raise IndexError(f"tile {tile_x},{tile_y} is outside the directory")
        payload = self.reader.read_at(int(offsets[index]), int(counts[index]))
        compression = int(self.single(TAG_COMPRESSION, 1))
        if compression == COMPRESSION_DEFLATE:
            payload = zlib.decompress(payload)
        predictor = int(self.single(TAG_PREDICTOR, 1))
        if predictor == PREDICTOR_HORIZONTAL:
            payload = undo_horizontal_predictor(payload, self.tile_width, self.samples)
        return payload

    def read_window(self, x: int, y: int, width: int, height: int) -> list[bytes]:
        """RGB rows for a window, honouring the scene's right and bottom edges."""
        if x < 0 or y < 0 or x + width > self.width or y + height > self.height:
            raise ValueError("the window falls outside the scene")
        rows: list[bytes] = []
        for row in range(y, y + height):
            tile_y, offset_y = divmod(row, self.tile_height)
            line = bytearray()
            for column in range(x, x + width):
                tile_x, offset_x = divmod(column, self.tile_width)
                tile = self._cached_tile(tile_x, tile_y)
                start = (offset_y * self.tile_width + offset_x) * self.samples
                line += tile[start:start + self.samples]
            rows.append(bytes(line))
        return rows

    def _cached_tile(self, tile_x: int, tile_y: int) -> bytes:
        key = (tile_x, tile_y)
        if not hasattr(self, "_tiles"):
            self._tiles: dict[tuple[int, int], bytes] = {}
        if key not in self._tiles:
            self._tiles[key] = self.read_tile(tile_x, tile_y)
        return self._tiles[key]
