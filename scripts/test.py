
import math

def dir(u,v):
  if (v == 0):
    v = 0.000000001
  dd = math.atan(u / v)
  ddir = (dd * 180.00) / math.pi

  if (u > 0 and v > 0 ): # First Quad
    ddir = 180 + ddir
  elif (u > 0 and v < 0 ): # Second Quad
    ddir = 360 + ddir
  elif (u < 0 and v < 0 ): # Third Quad
    ddir = ddir
  elif (u < 0 and v > 0 ): # Fourth Quad
    ddir = 180 + ddir

  return int(math.fabs(ddir))


