"""Research-only exposure attribution. No alpha or causal identification is implied."""

from .core import Factor, Panel, fit, attribute, overlap, hedge_projection

__all__ = ["Factor", "Panel", "fit", "attribute", "overlap", "hedge_projection"]
