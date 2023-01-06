import unittest

import modular
import moo_grammar


class TestStack(unittest.TestCase):
    def test_cases(self):
        self.assertEqual(modular.stack('a b'), ['a b'])
        self.assertEqual(modular.stack('a;b;c'), ['a', 'b', 'c'])
        self.assertEqual(modular.stack('a;;b;c'), ['a;b', 'c'])
        self.assertEqual(modular.stack('a;;;b;c'), ['a;;b', 'c'])

    def test_moolist(self):
        d = '{{#2259, "Kat", 7, 1150598865, 1672909821}, {#249, "Q", 7, 1128798341, 1672898642}, {#4096, "client", 2, 1672707426, 1672890758}, {#3516, "Tyler Spivey", 7, 1252122156, 1672825696}, {#3636, "simon", 3, 1274652882, 1672521696}, {#2486, "pikachu", 3, 1226872309, 1671988686}, {#1143, "Quin", 3, 1670983437, 1671900968}, {#116, "Patrick W", 3, 1670982988, 1671531983}}'
        expected = [['#2259', '"Kat"', 7, 1150598865, 1672909821], ['#249', '"Q"', 7, 1128798341, 1672898642], ['#4096', '"client"', 2, 1672707426, 1672890758], ['#3516', '"Tyler Spivey"', 7, 1252122156, 1672825696], ['#3636', '"simon"', 3, 1274652882, 1672521696], ['#2486', '"pikachu"', 3, 1226872309, 1671988686], ['#1143', '"Quin"', 3, 1670983437, 1671900968], ['#116', '"Patrick W"', 3, 1670982988, 1671531983]]
        parsed = moo_grammar.parse_value(d)
        assert parsed == expected


if __name__ == '__main__':
    unittest.main()
