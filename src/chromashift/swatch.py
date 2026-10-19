"""Built-in swatch sheet and grid rendering (all assets generated in-repo)."""

from __future__ import annotations

from .color import parse_hex
from .png import Image

# A deliberately awkward, realistic UI set: the classic red/green status pair,
# a categorical chart series, and neutrals. Authored for this project.
BUILTIN_SWATCHES: list[tuple[str, str]] = [
    ("error", "#d32f2f"),
    ("success", "#2e7d32"),
    ("warning", "#f9a825"),
    ("info", "#1565c0"),
    ("red-500", "#ef4444"),
    ("orange-500", "#f97316"),
    ("amber-500", "#f59e0b"),
    ("yellow-500", "#eab308"),
    ("green-500", "#22c55e"),
    ("emerald-500", "#10b981"),
    ("teal-500", "#14b8a6"),
    ("cyan-500", "#06b6d4"),
    ("blue-500", "#3b82f6"),
    ("indigo-500", "#6366f1"),
    ("purple-500", "#a855f7"),
    ("pink-500", "#ec4899"),
    ("brown", "#8d6e63"),
    ("olive", "#9e9d24"),
    ("sky", "#4fc3f7"),
    ("mint", "#66bb6a"),
    ("coral", "#ff7043"),
    ("grape", "#7e57c2"),
    ("slate", "#455a64"),
    ("paper", "#fafafa"),
]

DEFAULT_COLUMNS = 8


def builtin_rgb() -> list[tuple[int, int, int]]:
    return [parse_hex(hx) for _, hx in BUILTIN_SWATCHES]


def render_grid(rows: list[list[tuple[int, int, int] | None]],
                columns: int = DEFAULT_COLUMNS, cell: int = 40, gap: int = 4,
                background: tuple[int, int, int, int] = (32, 32, 32, 255),
                empty: tuple[int, int, int, int] = (96, 96, 96, 255)) -> Image:
    """Render rows of colors as a square-cell grid image.

    ``None`` entries render as a placeholder gray (padding).
    """
    if columns < 1:
        raise ValueError("columns must be >= 1")
    rows = rows or []
    width = columns * cell + (columns - 1) * gap
    nrows = len(rows)
    height = nrows * cell + max(0, nrows - 1) * gap
    if height <= 0:
        raise ValueError("no rows to render")
    img = Image(width, height, bytearray(width * height * 4))
    bg = bytes(background)
    for i in range(0, len(img.pixels), 4):
        img.pixels[i:i + 4] = bg
    for ry, row in enumerate(rows):
        for cx in range(columns):
            color = row[cx] if cx < len(row) else None
            fill = empty if color is None else (color[0], color[1], color[2], 255)
            fb = bytes(fill)
            y0 = ry * (cell + gap)
            x0 = cx * (cell + gap)
            for y in range(y0, y0 + cell):
                for x in range(x0, x0 + cell):
                    off = (y * width + x) * 4
                    img.pixels[off:off + 4] = fb
    return img


def rows_of(colors: list[tuple[int, int, int] | None],
            columns: int = DEFAULT_COLUMNS) -> list[list[tuple[int, int, int] | None]]:
    """Chunk a flat color list into grid rows."""
    return [colors[i:i + columns] for i in range(0, len(colors), columns)] or [[]]


def swatch_sheet(columns: int = DEFAULT_COLUMNS) -> Image:
    """The built-in swatch grid (the `swatches` command's original image)."""
    return render_grid(rows_of(builtin_rgb(), columns), columns=columns)
