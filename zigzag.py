import typing
import numpy as np

# inspired by: https://github.com/nmayorov/jpeg-decoder/blob/master/src/util.h (appears to be gone)
def fill_zigzag(flat_table: typing.Iterable[int], block: np.array):
    rows, cols = block.shape
    i, j = 0, 0
    di, dj = -1, 1

    def pull_from_flat_table():
        for value in flat_table:
            yield value

    pull_flat_value = pull_from_flat_table()

    # for each diagonal
    for _ in range(rows + cols - 1):
        while i >= 0 and j >= 0 and i < rows and j < cols:
            block[i, j] = next(pull_flat_value)
            i += di
            j += dj

        i -= di
        j -= dj

        # swap direction of diagonal
        di *= -1
        dj *= -1

        if (i == 0 or i == (rows - 1)) and j < (cols - 1):
            j += 1
        else:
            i += 1
