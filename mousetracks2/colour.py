import colorsys
import random

from typing import Iterator


def generate_colour_schemes() -> Iterator[str]:
    """Generate random colour schemes using colour theory strategies.
    Each palette is sorted by lightness.

    Yields:
        A string representing a colour scheme, with each colour joined by "To".
        Example: "#2a8a8aTo#32a8a8To#a88e32To#3257a8"
    """
    def _hsl_to_hex(h: float, s: float, l: float) -> str:
        """Converts HSL values (0-1 range) to an RGB hex string."""
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return f'#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}'

    def _generate_complementary() -> list[tuple[float, float, float]]:
        """Generates a high-contrast palette from two opposite colours on the wheel."""
        base_hue = random.random()
        saturation = random.uniform(0.75, 1.0)
        lightness = random.uniform(0.5, 0.6)

        hues = [base_hue, (base_hue + 0.5) % 1.0]

        colours = []
        for i in range(num_colours):
            hue = hues[i % len(hues)]
            l_offset = random.uniform(-0.25, 0.25)
            s_offset = random.uniform(-0.2, 0)

            new_lightness = max(0.15, min(0.85, lightness + l_offset))
            new_saturation = max(0.6, min(1.0, saturation + s_offset))
            colours.append((hue, new_saturation, new_lightness))
        return colours

    def _generate_triadic() -> list[tuple[float, float, float]]:
        """Generates a vibrant palette from three evenly spaced colours."""
        base_hue = random.random()
        saturation = random.uniform(0.7, 1.0)
        lightness = random.uniform(0.5, 0.65)

        hues = [base_hue, (base_hue + 1/3) % 1.0, (base_hue + 2/3) % 1.0]

        colours = []
        for i in range(num_colours):
            hue = hues[i % len(hues)]
            l_offset = random.uniform(-0.25, 0.25)
            new_lightness = max(0.15, min(0.85, lightness + l_offset))
            colours.append((hue, saturation, new_lightness))
        return colours

    def _generate_split_complementary() -> list[tuple[float, float, float]]:
        """Generates a high-contrast palette."""
        base_hue = random.random()
        saturation = random.uniform(0.75, 1.0)
        lightness = random.uniform(0.45, 0.6)

        complement_hue = (base_hue + 0.5) % 1.0
        split_offset = random.uniform(0.08, 0.12)

        hues = [
            base_hue,
            (complement_hue - split_offset + 1.0) % 1.0,
            (complement_hue + split_offset) % 1.0
        ]

        colours = []
        for i in range(num_colours):
            hue = hues[i % len(hues)]
            l_offset = random.uniform(-0.2, 0.2)
            s_offset = random.uniform(-0.1, 0)

            new_lightness = max(0.15, min(0.85, lightness + l_offset))
            new_saturation = max(0.7, min(1.0, saturation + s_offset))
            colours.append((hue, new_saturation, new_lightness))
        return colours

    # Calculate random of number of colours, weighted to 4
    num_colour_choices = []
    for i in range(20):
        num_colour_choices.append(4)
        check = random.random()
        if check < 0.2:
            num_colour_choices[i] -= 1
        elif check > 0.8:
            num_colour_choices[i] += 1
            while random.random() > 0.8:
                num_colour_choices[i] += 1

    strategies = [
        _generate_complementary,
        _generate_split_complementary,
        _generate_triadic,
    ]

    while True:
        num_colours = random.choice(num_colour_choices)
        strategy = random.choice(strategies)
        hsl_colours = strategy()

        # Sort by lightness
        hsl_colours.sort(key=lambda x: x[2], reverse=random.choice([True, False]))

        yield 'To'.join(_hsl_to_hex(h, s, l) for h, s, l in hsl_colours)
