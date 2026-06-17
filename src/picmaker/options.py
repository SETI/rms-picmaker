"""Configuration dataclass for :func:`picmaker.pipeline.images_to_pics`.

:class:`PicmakerOptions` consolidates the ~45 keyword arguments accepted
by :func:`picmaker.pipeline.images_to_pics` into a single value object,
and owns the cross-field mutex / value-validity checks that previously
lived inline in both ``picmaker.cli._normalize_and_validate`` (the
private helper that builds the CLI's option dict) and
:func:`picmaker.pipeline.images_to_pics`.

The public function signature of
:func:`picmaker.pipeline.images_to_pics` is unchanged for backward
compatibility — internally it builds a :class:`PicmakerOptions` and
calls :meth:`PicmakerOptions.validate` so the duplicated mutex checks
live in exactly one place.
"""

from dataclasses import asdict, dataclass
from typing import Any

PDS3_LABEL_METHODS: tuple[str, ...] = ('strict', 'loose', 'compound', 'fast')

# Names of PicmakerOptions fields forwarded to instrument read_file() as **kwargs.
# Add the name of any new instrument-specific option here alongside its field definition above.
READ_FILE_KWARGS: tuple[str, ...] = ('mosaic', 'pds3_label_method')


@dataclass
class PicmakerOptions:
    """All post-normalization knobs that drive the pipeline.

    Each field's default matches the corresponding kwarg default on
    :func:`picmaker.pipeline.images_to_pics`. Call :meth:`validate` once
    after construction (or after any in-place mutation) to enforce the
    cross-field invariants.

    The :meth:`to_kwargs` and :meth:`from_kwargs` helpers let the legacy
    ``**option_dict`` call form continue to work unchanged.
    """

    # control
    replace: str = 'all'
    proceed: bool = False
    # output
    extension: str | None = 'jpg'
    suffix: str = ''
    strip: Any = None
    quality: int = 75
    twobytes: bool = False
    # selection
    bands: Any = None
    lines: Any = None
    samples: Any = None
    obj: Any = None
    pointer: Any = None
    pds3_label_method: str = 'strict'
    # sizing
    size: Any = None
    scale: Any = (100.0, 100.0)
    crop: Any = None
    frame: Any = None
    pad: bool = False
    pad_color: Any = 'black'
    frame_max: int | None = None
    # layout
    wrap: bool = False
    wrap_ratio: float | None = None
    overlap: tuple[float, float] = (0.0, 0.0)
    gap_size: int = 1
    gap_color: Any = 'white'
    mosaic: bool = False
    # scaling
    valid: Any = None
    limits: Any = None
    percentiles: Any = None
    trim: int = 0
    trim_zeros: bool = False
    footprint: int = 0
    histogram: bool = False
    # enhancement
    colormap: Any = None
    below_color: Any = None
    above_color: Any = None
    invalid_color: Any = None
    gamma: float = 1.0
    tint: bool = False
    # orientation
    display_upward: bool = False
    display_downward: bool = False
    rotate: Any = None
    # processing
    filter_name: str = 'NONE'
    zebra: bool = False

    def validate(self) -> None:
        """Run cross-field mutex / value-validity checks.

        Raises:
            ValueError: When two options that cannot be set together are
                both set, or when ``twobytes`` is combined with a
                non-TIFF extension or a non-trivial filter.
        """
        if self.mosaic and self.bands is not None:
            raise ValueError('mosaic and bands options are incompatible')
        if self.frame is not None and self.size is not None:
            raise ValueError('frame and size options are incompatible')
        if self.frame is not None and self.wrap_ratio:
            raise ValueError('frame and wrap_ratio options are incompatible')
        if self.display_upward and self.display_downward:
            raise ValueError('--up and --down options are incompatible')
        if self.twobytes:
            if (
                self.extension is not None
                and self.extension.lower()[:3] != 'tif'
            ):
                raise ValueError('only tiffs can be written in 16-bit mode')
            # ``filter_name`` is typed as ``str`` with default ``'NONE'``,
            # so we only need to compare the value directly.
            if self.filter_name.lower() != 'none':
                raise ValueError('16-bit filter options are not supported')
        if self.pds3_label_method not in PDS3_LABEL_METHODS:
            raise ValueError(
                f'invalid pds3_label_method {self.pds3_label_method!r}; '
                f'must be one of {PDS3_LABEL_METHODS}'
            )

    def to_kwargs(self) -> dict[str, Any]:
        """Return a kwargs dict that unpacks into the pipeline entry point.

        Specifically, the dict can be passed as
        ``picmaker.pipeline.images_to_pics(**options.to_kwargs())``.
        """
        return asdict(self)

    @classmethod
    def from_kwargs(cls, **kwargs: Any) -> 'PicmakerOptions':
        """Build a :class:`PicmakerOptions` from a kwargs dict."""
        return cls(**kwargs)


__all__ = ['PDS3_LABEL_METHODS', 'READ_FILE_KWARGS', 'PicmakerOptions']
