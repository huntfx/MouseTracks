from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, Generic, TypeVar

from ..components import ipc
from ..enums import BlendMode, Channel

T = TypeVar('T')


@dataclass
class RenderOption(Generic[T]):
    """Store one value per render category.

    Layer settings such as blur and contrast have independent values for
    each render type, so switching type on a layer recalls the right value.
    """

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
    """All settings for a single layer in the render stack."""

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

    def view(self, render_type: ipc.RenderType) -> LayerView:
        """Return a view of this layer for a specific render type."""
        return LayerView(self, render_type)


class LayerView:
    """A specific render type of a LayerOption."""

    __slots__ = ('_layer', '_render_type')

    def __init__(self, layer: LayerOption, render_type: ipc.RenderType) -> None:
        self._layer = layer
        self._render_type = render_type

    @property
    def render_colour(self) -> str:
        """Name of the colour map used for rendering."""
        return self._layer.render_colour.get(self._render_type)

    @render_colour.setter
    def render_colour(self, value: str) -> None:
        self._layer.render_colour.set(self._render_type, value)

    @property
    def contrast(self) -> float:
        """Contrast applied to the colour map."""
        return self._layer.contrast.get(self._render_type)

    @contrast.setter
    def contrast(self, value: float) -> None:
        self._layer.contrast.set(self._render_type, value)

    @property
    def padding(self) -> int:
        """Padding added around the render output."""
        return self._layer.padding.get(self._render_type)

    @padding.setter
    def padding(self, value: int) -> None:
        self._layer.padding.set(self._render_type, value)

    @property
    def clipping(self) -> float:
        """Fraction of low values clipped before colour mapping."""
        return self._layer.clipping.get(self._render_type)

    @clipping.setter
    def clipping(self, value: float) -> None:
        self._layer.clipping.set(self._render_type, value)

    @property
    def blur(self) -> float:
        """Amount of Gaussian blur applied before rendering."""
        return self._layer.blur.get(self._render_type)

    @blur.setter
    def blur(self, value: float) -> None:
        self._layer.blur.set(self._render_type, value)

    @property
    def linear(self) -> bool:
        """Use linear interpolation when scaling the data."""
        return self._layer.linear.get(self._render_type)

    @linear.setter
    def linear(self, value: bool) -> None:
        self._layer.linear.set(self._render_type, value)

    @property
    def invert(self) -> bool:
        """Reverse the colour map."""
        return self._layer.invert.get(self._render_type)

    @invert.setter
    def invert(self, value: bool) -> None:
        self._layer.invert.set(self._render_type, value)

    @property
    def show_left_clicks(self) -> bool:
        """Include left mouse button clicks in the render."""
        return self._layer.show_left_clicks

    @show_left_clicks.setter
    def show_left_clicks(self, value: bool) -> None:
        self._layer.show_left_clicks = value

    @property
    def show_middle_clicks(self) -> bool:
        """Include middle mouse button clicks in the render."""
        return self._layer.show_middle_clicks

    @show_middle_clicks.setter
    def show_middle_clicks(self, value: bool) -> None:
        self._layer.show_middle_clicks = value

    @property
    def show_right_clicks(self) -> bool:
        """Include right mouse button clicks in the render."""
        return self._layer.show_right_clicks

    @show_right_clicks.setter
    def show_right_clicks(self, value: bool) -> None:
        self._layer.show_right_clicks = value


class LayerManager:
    """Handles the layer stack state and outputs it as IPC messages."""

    def __init__(self) -> None:
        self._layers: dict[int, LayerOption] = {}
        self._layer_counter: int = 0
        self._selected_layer: int = 0

    @property
    def selected_layer(self) -> LayerOption:
        """Get the selected layer data."""
        return self._layers[self._selected_layer]

    def __getitem__(self, layer_id: int) -> LayerOption:
        return self._layers[layer_id]

    def add(self, option: LayerOption) -> int:
        """Add a layer and return its ID."""
        layer_id = self._layer_counter
        self._layers[layer_id] = option
        self._layer_counter += 1
        return layer_id

    def clear(self) -> None:
        """Remove all layers and reset the counter."""
        self._layers.clear()
        self._layer_counter = 0
        self._selected_layer = 0

    def select(self, layer_id: int) -> LayerOption:
        """Set the active layer by ID and return it."""
        self._selected_layer = layer_id
        return self._layers[layer_id]

    def render_layers(self,
        layer_items: Iterable[tuple[int, bool]],
        profile: str,
        file_path: str | None,
        width: int | None,
        height: int | None,
        sampling: int,
        lock_aspect: bool,
        show_keyboard_time: bool,
        interpolation_order: Literal[0, 1, 2, 3, 4, 5],
    ) -> Iterator[ipc.RenderLayer]:
        """Yield a RenderLayer for each item in the layer stack."""
        for layer_id, visible in layer_items:
            layer_option = self._layers[layer_id]
            render_type = layer_option.render_type
            request = ipc.RenderRequest(
                type=render_type,
                width=width,
                height=height,
                lock_aspect=lock_aspect,
                profile=profile,
                file_path=file_path,
                colour_map=layer_option.render_colour.get(render_type),
                padding=layer_option.padding.get(render_type),
                sampling=sampling,
                contrast=layer_option.contrast.get(render_type),
                clipping=layer_option.clipping.get(render_type),
                blur=layer_option.blur.get(render_type),
                linear=layer_option.linear.get(render_type),
                invert=layer_option.invert.get(render_type),
                show_left_clicks=layer_option.show_left_clicks,
                show_middle_clicks=layer_option.show_middle_clicks,
                show_right_clicks=layer_option.show_right_clicks,
                show_keyboard_time=show_keyboard_time,
                interpolation_order=interpolation_order,
                layer_visible=visible,
            )
            yield ipc.RenderLayer(request, layer_option.blend_mode, layer_option.channels, layer_option.opacity)


class Preset:
    """Base class for layer presets."""

    name: ClassVar[str]
    _registry: ClassVar[dict[str, type[Preset]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Register each subclass by name on definition."""
        super().__init_subclass__(**kwargs)
        Preset._registry[cls.name] = cls

    @classmethod
    def get(cls, name: str) -> type[Preset]:
        """Look up a preset class by name."""
        return cls._registry[name]

    @classmethod
    def names(cls) -> list[str]:
        """Return all registered preset names."""
        return list(cls._registry)

    @classmethod
    def build(cls) -> Iterator[LayerOption]:
        """Yield the layers that make up this preset."""
        return
        yield


class Reset(Preset):
    """Reset to a single default movement layer."""

    name = 'Reset'

    @classmethod
    def build(cls) -> Iterator[LayerOption]:
        yield LayerOption(ipc.RenderType.MouseMovement)


class HeatmapOverlay(Preset):
    """Click heatmap overlaid on movement tracks using Luminance Mask blending."""

    name = 'Heatmap Overlay'

    @classmethod
    def build(cls) -> Iterator[LayerOption]:
        yield LayerOption(ipc.RenderType.MouseMovement)

        l1 = LayerOption(ipc.RenderType.SingleClick, blend_mode=BlendMode.LuminanceMask, opacity=50)
        l1.clipping.heatmap = 0.01
        l1.contrast.heatmap = 1.5
        yield l1


class HeatmapTracks(Preset):
    """Position heatmap multiplied over white movement tracks."""

    name = 'Heatmap Tracks'

    @classmethod
    def build(cls) -> Iterator[LayerOption]:
        l0 = LayerOption(ipc.RenderType.MouseMovement)
        l0.render_colour.movement = 'Chalk'
        yield l0

        l1 = LayerOption(ipc.RenderType.MousePosition, blend_mode=BlendMode.Multiply)
        l1.render_colour.heatmap = 'Inferno'
        l1.blur.heatmap = 0.001
        yield l1


class AlphaMultiply(Preset):
    """Uses a position heatmap on the alpha channel to fade out areas of low activity."""

    name = 'Alpha Multiply'

    @classmethod
    def build(cls) -> Iterator[LayerOption]:
        yield LayerOption(ipc.RenderType.MouseMovement)

        l1 = LayerOption(ipc.RenderType.MousePosition, blend_mode=BlendMode.Multiply, channels=Channel.A)
        l1.render_colour.heatmap = 'TransparentWhiteToWhite'
        l1.blur.heatmap = 0
        l1.clipping.heatmap = 0.85
        l1.contrast.heatmap = 0.5
        yield l1


class UrbanMoss(Preset):
    """Combines movement and speed data for an effect like moss growing on concrete."""

    name = 'Urban Moss'

    @classmethod
    def build(cls) -> Iterator[LayerOption]:
        l0 = LayerOption(ipc.RenderType.MouseMovement)
        l0.render_colour.movement = 'Chalk'
        yield l0

        l1 = LayerOption(ipc.RenderType.MouseSpeed)
        l1.render_colour.speed = 'TransparentBlackToBlackToGreen'
        yield l1


class Eraser(Preset):
    """Subtracts clicks from movement tracks, like a pencil drawing that's been rubbed out."""

    name = 'Eraser'

    @classmethod
    def build(cls) -> Iterator[LayerOption]:
        l0 = LayerOption(ipc.RenderType.MouseMovement)
        l0.render_colour.movement = 'Graphite'
        yield l0

        l1 = LayerOption(ipc.RenderType.SingleClick, blend_mode=BlendMode.Subtract, channels=Channel.A)
        l1.render_colour.heatmap = 'TransparentWhiteToWhite'
        l1.clipping.heatmap = 0.2
        l1.contrast.heatmap = 1.5
        yield l1


class Plasma(Preset):
    """Overlay blend mode for high contrast and deep colours."""

    name = 'Plasma'

    @classmethod
    def build(cls) -> Iterator[LayerOption]:
        l0 = LayerOption(ipc.RenderType.MouseMovement)
        l0.render_colour.movement = 'Demon'
        yield l0

        l1 = LayerOption(ipc.RenderType.SingleClick, blend_mode=BlendMode.Overlay)
        l1.render_colour.heatmap = 'Riptide'
        l1.clipping.heatmap = 0.01
        l1.blur.heatmap = 0.02
        yield l1


class RGBClicks(Preset):
    """Three click renders with separate colour channels: left=red, middle=green, right=blue."""

    name = 'RGB Clicks'

    @classmethod
    def build(cls) -> Iterator[LayerOption]:
        l0 = LayerOption(ipc.RenderType.SingleClick, blend_mode=BlendMode.Screen, channels=Channel.R | Channel.A)
        l0.render_colour.heatmap = 'Chalk'
        l0.show_middle_clicks = False
        l0.show_right_clicks = False
        yield l0

        l1 = LayerOption(ipc.RenderType.SingleClick, blend_mode=BlendMode.Screen, channels=Channel.G | Channel.A)
        l1.render_colour.heatmap = 'Chalk'
        l1.show_left_clicks = False
        l1.show_right_clicks = False
        yield l1

        l2 = LayerOption(ipc.RenderType.SingleClick, blend_mode=BlendMode.Screen, channels=Channel.B | Channel.A)
        l2.render_colour.heatmap = 'Chalk'
        l2.show_left_clicks = False
        l2.show_middle_clicks = False
        yield l2
