import numpy as np
from .common import get_dtype, print, listen

def Isend(self, dest, world, dtype=None, ndim=None, shape=None, listen_request=False, verbose=False, **kwargs):
    """Isend wrapper.

    Automatically determines data type and shape. Must be accompanied by Irecv on the dest rank.

    Parameters
    ----------
    dest : int
        Rank to send to
    world : mpi4py.MPI.COMM_WORLD
        MPI communicator
    dtype : dtype, optional
        Pre-determined data type if known. Faster
        Defaults to None.
    ndim : int, optional
        Number of dimension if known. Faster
        Defaults to None.
    shape : ints, optional
        values shape if known. Faster
        Defaults to None.
    """
    if listen_request:
        dest = listen(world=world)

    # Send the data type
    if dtype is None:
        dtype = get_dtype(self, world, world.rank)
        if verbose:
            print(f'isend {dtype=}', world=world)
        world.isend(dtype, dest=dest)

    assert (not dtype == 'list'), TypeError("Cannot Isend/Irecv a list")

    if dtype == 'str':
        world.isend(self, dest=dest)
        return

    # Broadcast the number of dimensions
    if ndim is None:
        ndim = np.ndim(self)
        if verbose:
            print(f'isend {ndim=}', world=world)
        Isend(ndim, dest=dest, world=world, ndim=0, dtype=np.int64)

    if (ndim == 0):  # For a single number
        this = np.full(1, self, dtype=dtype)  # Initialize on each worker
        if verbose:
            print(f'isend {this=}', world=world)
        world.Isend(this, dest=dest)

    elif (ndim == 1):  # For a 1D array
        if shape is None:
            Isend(np.size(self), dest=dest, world=world, ndim=0, dtype=np.int64)
        world.Isend(self, dest=dest)

    elif (ndim > 1):  # nD Array
        if shape is None:
            Isend(np.asarray(self.shape, dtype=np.int64), dest=dest, world=world, shape=ndim, dtype=np.int64)
        world.Isend(self, dest=dest)

    return dest