"""
This module is for reading/writing PyTurbSim data objects to
TurbSim/Aerodyn format binary files.

The functions in this module were translated directly from the
original TSsubs.f90 file.

"""
import time
from .._version import __version__, __prog_name__, __version_date__
from struct import pack, unpack
import numpy as np
from .base import e, convname


def write(fname, tsdat):
    """
    Write the data to a AeroDyn-/TurbSim-format binary file.

    Parameters
    ----------
    fname : str
            the filename to which the data should be written.
    tsdata : :class:`tsdata <pyts.main.tsdata>`
             The 'tsdata' object that contains the data.

    """
    ts = tsdat.utotal
    intmin = -32768
    intrng = 65536
    u_minmax = np.empty((3, 2), dtype=np.float32)
    u_off = np.empty((3), dtype=np.float32)
    u_scl = np.empty((3), dtype=np.float32)
    desc_str = 'generated by %s v%s, %s.' % (
        __prog_name__,
        __version__,
        time.strftime('%b %d, %Y, %H:%M (%Z)', time.localtime()))
    # Calculate the ranges:
    out = np.empty(tsdat.shape, dtype=np.int16)
    for ind in range(3):
        u_minmax[ind] = ts[ind].min(), ts[ind].max()
        if u_minmax[ind][0] == u_minmax[ind][1]:
            u_scl[ind] = 1
        else:
            u_scl[ind] = intrng / np.diff(u_minmax[ind])
        u_off[ind] = intmin - u_scl[ind] * u_minmax[ind, 0]
        out[ind] = (ts[ind] * u_scl[ind] + u_off[ind]).astype(np.int16)
    fl = file(convname(fname, '.bts'), 'wb')
    fl.write(pack(e + 'h4l12fl',
                  7,
                  tsdat.grid.n_z,
                  tsdat.grid.n_y,
                  tsdat.grid.n_tower,
                  tsdat.shape[-1],
                  tsdat.grid.dz,
                  tsdat.grid.dy,
                  tsdat.dt,
                  tsdat.UHUB,
                  tsdat.grid.zhub,
                  tsdat.grid.z[0],
                  u_scl[0],
                  u_off[0],
                  u_scl[1],
                  u_off[1],
                  u_scl[2],
                  u_off[2],
                  len(desc_str)))
    fl.write(desc_str)
    # Swap the y and z indices so that fortran-order writing agrees with the file format.
    # Also, we swap the order of z-axis to agree with the file format.
    # Write the data so that the first index varies fastest (F order).
    # The indexes vary in the following order:
    # component (fastest), y-index, z-index, time (slowest).
    fl.write(np.rollaxis(out[:, ::-1], 2, 1).tostring(order='F'))
    fl.close()


def read(fname):
    """
    Read AeroDyn/TurbSim format (.bts) full-field time-series binary
    data files.

    Parameters
    ----------
    fname : str
            The filename from which to read the data.

    Returns
    -------
    tsdata : array_like
             An array of the turbulence data. !This needs to be fixed
             to be a tsdata object!

    """
    ## !!!FIXTHIS, to be symmetric with 'write' this should return a tsData object:
    ## *tsdat*  - A tsdata object that contains the data.
    u_scl = np.zeros(3, np.float32)
    u_off = np.zeros(3, np.float32)
    fl = file(fname, 'rb')
    (junk,
     n_z,
     n_y,
     n_tower,
     n_t,
     dz,
     dy,
     dt,
     uhub,
     zhub,
     z0,
     u_scl[0],
     u_off[0],
     u_scl[1],
     u_off[1],
     u_scl[2],
     u_off[2],
     strlen) = unpack(e + 'h4l12fl', fl.read(70))
    #print fname, u_scl, u_off
    #desc_str = fl.read(strlen)
    nbt = 3 * n_y * n_z * n_t
    out = np.rollaxis(np.fromstring(fl.read(2 * nbt), dtype=np.int16).astype(
        np.float32).reshape([3, n_y, n_z, n_t], order='F'), 2, 1)[:, ::-1]
    out -= u_off[:, None, None, None]
    out /= u_scl[:, None, None, None]
    return out
