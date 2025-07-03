from enum import Enum, IntFlag, auto


class BlendMode(Enum):
    """Layer blending modes."""

    Normal = auto()
    Replace = auto()
    Overlay = auto()
    Screen = auto()
    LuminanceMask = auto()
    SoftLight = auto()
    HardLight = auto()
    ColourDodge = auto()
    ColourBurn = auto()
    Add = auto()
    Subtract = auto()
    Multiply = auto()
    Divide = auto()
    Difference = auto()
    Maximum = auto()
    Minimum = auto()


class Channel(IntFlag):
    """RGB channels."""

    R = auto()
    G = auto()
    B = auto()
    A = auto()
    RGB = R | G | B
    RGBA = R | G | B | A
    Alpha = A

    @classmethod
    def get_indices(cls, mask: int) -> list[int]:
        """Converts the bitmask into a list of array indices."""
        channels = [cls.R, cls.G, cls.B, cls.A]
        return [i for i, val in enumerate(channels) if mask & val]
