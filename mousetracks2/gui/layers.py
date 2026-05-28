from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from ..components import ipc
from ..enums import BlendMode, Channel

T = TypeVar('T')


@dataclass
class RenderOption(Generic[T]):
    """Store different values per render type."""

    movement: T
    speed: T
    heatmap: T
    keyboard: T

    def get(self, render_type: ipc.RenderType) -> T:
        """Get the value for a render type."""
        match render_type:
            case (ipc.RenderType.MouseMovement | ipc.RenderType.ThumbstickMovement):
                return self.movement
            case ipc.RenderType.MouseSpeed | ipc.RenderType.ThumbstickSpeed:
                return self.speed
            case (ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick | ipc.RenderType.HeldClick
                  | ipc.RenderType.ThumbstickPosition | ipc.RenderType.MousePosition):
                return self.heatmap
            case ipc.RenderType.KeyboardHeatmap:
                return self.keyboard
            case _:
                raise NotImplementedError(f'Unsupported render type: {render_type}')

    def set(self, render_type: ipc.RenderType, value: T) -> None:
        """Set the value for a render type."""
        match render_type:
            case (ipc.RenderType.MouseMovement | ipc.RenderType.ThumbstickMovement):
                self.movement = value
            case ipc.RenderType.MouseSpeed | ipc.RenderType.ThumbstickSpeed:
                self.speed = value
            case (ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick | ipc.RenderType.HeldClick
                  | ipc.RenderType.ThumbstickPosition | ipc.RenderType.MousePosition):
                self.heatmap = value
            case ipc.RenderType.KeyboardHeatmap:
                self.keyboard = value
            case _:
                raise NotImplementedError(f'Unsupported render type: {render_type}')


@dataclass
class LayerOption:
    render_type: ipc.RenderType
    blend_mode: BlendMode = BlendMode.Normal
    channels: Channel = Channel.RGBA
    opacity: int = 100
    render_colour: RenderOption = field(default_factory=lambda: RenderOption('Ice', 'Ice', 'Jet', 'Aqua'))
    contrast: RenderOption = field(default_factory=lambda: RenderOption(1.0, 1.0, 1.0, 1.0))
    padding: RenderOption = field(default_factory=lambda: RenderOption(0, 0, 0, 0))
    clipping: RenderOption = field(default_factory=lambda: RenderOption(0.0, 0.0, 0.001, 0.0))
    blur: RenderOption = field(default_factory=lambda: RenderOption(0.0, 0.0, 0.0125, 0.0))
    linear: RenderOption = field(default_factory=lambda: RenderOption(False, True, True, False))
    invert: RenderOption = field(default_factory=lambda: RenderOption(False, False, False, False))
    show_left_clicks: bool = True
    show_middle_clicks: bool = True
    show_right_clicks: bool = True
