import sys
import numpy as np
import progressbar


def get_dtype(self, world=None, rank=0):
    out = None

    if world is not None:
        if world.rank == rank:
            out = mpiu_dtype(self)
    return out

def mpiu_dtype(self):
    out = str(self.__class__.__name__)  # Otherwise use the type finder
    if 'ndarray' in out:
        out = str(self.dtype)
    return out

def mpiu_time(world=None):
    from mpi4py.MPI import Wtime
    import time
    if world is None:
        return time.time()
    else:
        return Wtime()

def print(*args, world=None, rank=None, **kwargs):
    """Print to the screen with a flush.

    Parameters
    ----------
    aStr : str
        A string to print.
    end : str
        string appended after the last value, default is a newline.
    world : mpi4py.MPI.Comm
        MPI parallel communicator.
    rank : int
        The rank to print from, default is the head rank, 0.

    """
    msg = ' '.join(str(x) for x in args) + "\n"
    if world is None:
        sys.stdout.write(msg)
    else:
        if rank is None:
            msg = f"rank {world.rank}:" + msg
            sys.stdout.write(msg)
        else:
            if (world.rank == rank):
                sys.stdout.write(msg)
    sys.stdout.flush()

def load_balance(shape, n_chunks):

    if np.ndim(shape) <= 1:
        return load_balance_1d(shape, n_chunks)
    elif np.ndim(shape) == 2:
        return load_balance_1d(shape, n_chunks)
    elif np.ndim(shape) == 3:
        return load_balance_1d(shape, n_chunks)
    assert False, ValueError("Can only go up to 3d.")

def load_balance_1d(N, n_chunks):
    """Splits the length of an array into a number of chunks. Load balances the chunks in a shrinking arrays fashion.

    Given length, N, split N up into n_chunks and return the starting index and size of each chunk.
    After being split equally among the chunks, the remainder is distributed so that chunks 0:remainder
    get +1 in size. e.g. N=10, n_chunks=3 would return starts=[0,4,7] chunks=[4,3,3]

    Parameters
    ----------
    N : int
        A size to split into chunks.
    n_chunks : int
        The number of chunks to split N into. Usually the number of ranks, world.size.

    Returns
    -------
    starts : ndarray of ints
        The starting indices of each chunk.
    chunks : ndarray of ints
        The size of each chunk.

    """
    chunks = np.full(n_chunks, fill_value=N/n_chunks, dtype=np.int64)
    mod = np.int64(N % n_chunks)
    chunks[:mod] += 1
    starts = np.cumsum(chunks) - chunks[0]
    if (mod > 0):
        starts[mod:] += 1
    return starts, chunks


def load_balance_2d(shape, n_chunks):
    """Splits the shape of a 2D array into n_chunks.

    The chunks are as close in size as possible.
    The larger axes have more chunks along that dimension.

    Parameters
    ----------
    shape : ints
        2D shape to split
    n_chunks : int
        Number of chunks

    Returns
    -------
    starts : ints
        Starting indices of each chunk.  Has shape (n_chunks, 2)
    chunks : ints
        Size of each chunk. Has shape (n_chunks, 2)

    """

    assert n_chunks % 2 == 0, ValueError("n_chunks must be even.")

    target = shape / np.linalg.norm(shape)
    best = None
    bestFit = 1e20
    for i in range(2, np.int64(n_chunks/2)+1):
        j = int(n_chunks/(i))
        nBlocks = np.asarray([i, j])
        total = np.prod(nBlocks)

        if total == n_chunks:
            fraction = nBlocks / np.linalg.norm(nBlocks)
            fit = np.linalg.norm(fraction - target)
            if fit < bestFit:
                best = nBlocks
                bestFit = fit

    s0, c0 = load_balance_1d(shape[0], best[0])
    s1, c1 = load_balance_1d(shape[1], best[1])

    a = np.repeat(s0, int(n_chunks/s0.size))
    b = np.tile(np.repeat(s1, int(n_chunks/(s0.size*s1.size))), s0.size)
    starts = np.vstack([a, b]).T

    a = np.repeat(c0, int(n_chunks/c0.size))
    b = np.tile(np.repeat(c1, int(n_chunks/(c0.size*c1.size))), c0.size)
    chunks = np.vstack([a, b]).T

    return starts, chunks

def load_balance_3d(shape, n_chunks):
    """Splits the shape of a 3D array into n_chunks.

    The chunks are as close in size as possible.
    The larger axes have more chunks along that dimension.

    Parameters
    ----------
    shape : ints
        3D shape to split
    n_chunks : int
        Number of chunks

    Returns
    -------
    starts : ints
        Starting indices of each chunk.  Has shape (n_chunks, 3)
    chunks : ints
        Size of each chunk. Has shape (n_chunks, 3)

    """

    # Find the "optimal" three product whose prod equals n_chunks
    # and whose relative amounts match as closely to shape as possible.

    assert n_chunks % 2 == 0, ValueError("n_chunks must be even.")

    target = shape / np.linalg.norm(shape)
    best = None
    bestFit = 1e20
    for i in range(1, int(n_chunks/2)+1):
        for j in range(1, int(n_chunks/i)):
            k = int(n_chunks/(i*j))
            nBlocks = np.asarray([i, j, k])
            total = np.prod(nBlocks)

            if total == n_chunks:
                fraction = nBlocks / np.linalg.norm(nBlocks)
                fit = np.linalg.norm(fraction - target)
                if fit < bestFit:
                    best = nBlocks
                    bestFit = fit

    s0, c0 = load_balance_1d(shape[0], best[0])
    s1, c1 = load_balance_1d(shape[1], best[1])
    s2, c2 = load_balance_1d(shape[2], best[2])

    a = np.repeat(s0, int(n_chunks/s0.size))
    b = np.tile(np.repeat(s1, int(n_chunks/(s0.size*s1.size))), s0.size)
    c = np.tile(s2, int(n_chunks/s2.size))
    starts = np.vstack([a, b, c]).T

    a = np.repeat(c0, int(n_chunks/c0.size))
    b = np.tile(np.repeat(c1, int(n_chunks/(c0.size*c1.size))), c0.size)
    c = np.tile(c2, int(n_chunks/c2.size))
    chunks = np.vstack([a, b, c]).T

    return starts, chunks

def prange(*args, world, root=0, **kwargs):
        """Generate a loop range.

        Tracks progress on the master rank only if parallel.

        Parameters
        ----------
        value : int
            Size of the loop to generate
        """
        bar = range(*args, **kwargs)

        if world.rank == root:
            Bar = progressbar.ProgressBar()
            bar = Bar(bar)
        return bar
