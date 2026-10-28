"""Fast distance-transform morphology (same radii in mm as the old ball structuring elements)."""
import numpy as np
from scipy import ndimage as ndi
H0 = 0.8
def dil(m, r, H=H0): return ndi.distance_transform_edt(~m, sampling=H) <= r
def ero(m, r, H=H0): return ndi.distance_transform_edt(m, sampling=H) > r
def clo(m, r, H=H0): return ero(dil(m, r, H), r, H)
def opn(m, r, H=H0): return dil(ero(m, r, H), r, H)
