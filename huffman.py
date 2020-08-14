import typing as T

Node = T.Union[int, T.List["Node"]]


class Huffman(object):
    def __init__(
        self, symbols_per_bit_length: T.List[int], symbols: T.List[T.List[int]]
    ):
        self.root = []

        for bit_length, symbol_count in enumerate(symbols_per_bit_length, 1):
            print(f"filling {symbol_count} {bit_length}-bit codes")
            symbols_at_depth = symbols[bit_length - 1]
            for i in range(symbol_count):
                self.bits_from_lengths(self.root, symbols_at_depth[i], bit_length)

    def bits_from_lengths(self, root: Node, symbol: int, bit_length: int):
        if not isinstance(root, list):
            return False

        if bit_length == 0:
            if len(root) < 2:
                root.append(symbol)

                return True
            return False

        for i in [0, 1]:
            if len(root) == i:
                root.append([])
            if self.bits_from_lengths(root[i], symbol, bit_length - 1):
                return True

    def __getitem__(self, key_list: T.List[int]):
        level = self.root
        for key in key_list:
            level = level[key]

        return level

