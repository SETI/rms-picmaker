"""Configuration dataclass for :func:`picmaker.pipeline.images_to_pics`.

:class:`PicmakerOptions` consolidates the ~45 keyword arguments accepted
by :func:`picmaker.pipeline.images_to_pics` into a single value object,
and owns the cross-field mutex / value-validity checks that previously
lived inline in both ``picmaker.cli._normalize_and_validate`` (the
private helper that builds the CLI's option dict) and
:func:`picmaker.pipeline.images_to_pics`.

:func:`picmaker.pipeline.images_to_pics` accepts a
:class:`PicmakerOptions` object directly (``options=``) or falls back to
constructing one from ``**kwargs`` for backward compatibility.  Either
way, :meth:`PicmakerOptions.normalize` and :meth:`PicmakerOptions.validate`
run before any I/O so the mutex checks live in exactly one place.
"""

from dataclasses import asdict, dataclass, field
from typing import Any

from picmaker._types import ObjectSelector

PDS3_LABEL_METHODS: tuple[str, ...] = ('strict', 'loose', 'compound', 'fast')
DEFAULT_PDS3_LABEL_METHOD: str = 'fast'

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
    strip: str | list[str] = field(default_factory=list)
    quality: int = 75
    twobytes: bool = False
    # selection
    bands: tuple[int, int] | None = None
    lines: tuple[int, int] | None = None
    samples: tuple[int, int] | None = None
    obj: ObjectSelector = None
    pointer: list[str] = field(default_factory=list)
    pds3_label_method: str = DEFAULT_PDS3_LABEL_METHOD
    # sizing
    size: Any = None
    scale: Any = (100.0, 100.0)
    crop: float | None = None
    frame: tuple[int, int] | None = None
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
    valid: tuple[float, float] | None = None
    limits: tuple[float, float] | None = None
    percentiles: tuple[float, float] | None = None
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

    def normalize(self) -> None:
        """Apply pipeline defaults that cannot be set at field-definition time.

        Call this before :meth:`validate` so that ``validate`` sees fully
        resolved values.  Calling it more than once is safe (idempotent).
        """
        if not self.pointer:
            self.pointer = ['IMAGE']
        if self.extension is None:
            self.extension = 'tiff' if self.twobytes else 'jpg'
        # bands must stay None for mosaic mode so validate() can catch the
        # incompatible-combination error when the user sets both explicitly.
        if self.bands is None and not self.mosaic:
            self.bands = (0, 1)

    def validate(self) -> None:
        """Run cross-field mutex / value-validity checks.

        Raises:
            ValueError: When two options that cannot be set together are
                both set, or when ``twobytes`` is combined with a
                non-TIFF extension or a non-trivial filter.
        """
        if self.replace not in ('all', 'none', 'warn', 'error'):
            raise ValueError(
                f'invalid replace value {self.replace!r}; '
                "must be one of 'all', 'none', 'warn', 'error'"
            )
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
        """Return a kwargs dict equivalent to this options object.

        The dict can be passed as
        ``picmaker.pipeline.images_to_pics(**options.to_kwargs())``
        for the flat-kwarg backward-compatible call form.
        """
        return asdict(self)

    @classmethod
    def from_kwargs(cls, **kwargs: Any) -> 'PicmakerOptions':
        """Build a :class:`PicmakerOptions` from a kwargs dict."""
        return cls(**kwargs)


__all__ = ['DEFAULT_PDS3_LABEL_METHOD', 'PDS3_LABEL_METHODS', 'READ_FILE_KWARGS', 'PicmakerOptions']
