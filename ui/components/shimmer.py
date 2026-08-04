from rich.text import Text

from ui.theme import rgb_parts

SHIMMER_BASE = rgb_parts("silver")
SHIMMER_PEAK = (255, 255, 255)
SHIMMER_WIDTH = 3.0
SHIMMER_SPEED = 0.28
SHIMMER_GAP = 10


def shimmer(label: str, frame: int) -> Text:
    head = (frame * SHIMMER_SPEED) % (len(label) + SHIMMER_GAP)
    text = Text()
    for index, char in enumerate(label):
        weight = max(0.0, 1.0 - (abs(index - head) / SHIMMER_WIDTH) ** 2)
        r, g, b = (
            round(base + (peak - base) * weight)
            for base, peak in zip(SHIMMER_BASE, SHIMMER_PEAK)
        )
        text.append(char, style=f"bold rgb({r},{g},{b})")
    return text
