"""Focused tests for tools/iatsim.py (no linker, no specimen): `python3 -m unittest tools.iatsim_tests`."""
import unittest

from tools import iatsim

LOG = """\
      Found __IMPORT_DESCRIPTOR_B
        Referenced in a.obj
        Loaded B.LIB(B.dll)
      Found __imp__Zed@4
        Referenced in a.obj
        Loaded B.LIB(B.dll)
      Found B_NULL_THUNK_DATA
        Referenced in B.LIB(B.dll)
        Loaded B.LIB(B.dll)
      Found __IMPORT_DESCRIPTOR_A
        Referenced in a.obj
        Loaded A.LIB(A.dll)
      Found _Alpha@8
        Referenced in a.obj
        Loaded A.LIB(A.dll)
      Found __imp__Beta@0
        Referenced in b.obj
        Loaded A.LIB(A.dll)
      Found A_NULL_THUNK_DATA
        Referenced in A.LIB(A.dll)
        Loaded A.LIB(A.dll)
    Discarded __imp__Beta@0 from A.LIB(A.dll)
"""


class Records(unittest.TestCase):
    def test_pass1_records_skip_descriptors_and_name_imports_plainly(self):
        records, discarded = iatsim.pass1_records(LOG)
        self.assertEqual(records, [("B.dll", "Zed"), ("B.dll", None), ("A.dll", "Alpha"), ("A.dll", "Beta"), ("A.dll", None)])
        self.assertEqual(discarded, {("A.dll", "Beta")})

    def test_predict_sorts_by_dll_name_drops_discarded_and_puts_the_null_thunk_last(self):
        records, discarded = iatsim.pass1_records(LOG)
        self.assertEqual(iatsim.predict(records, discarded), [("A.dll", "Alpha"), ("A.dll", None), ("B.dll", "Zed"), ("B.dll", None)])


class Qsort(unittest.TestCase):
    def test_short_arrays_are_selection_sorted_in_place(self):
        a = [5, 3, 9, 1, 7]
        iatsim.ms_qsort(a, lambda x, y: (x > y) - (x < y))
        self.assertEqual(a, [1, 3, 5, 7, 9])

    def test_larger_arrays_sort_and_equal_keys_keep_microsofts_order(self):
        recs = [(k % 3, i) for i, k in enumerate(range(30))]
        idx = list(range(30))
        iatsim.ms_qsort(idx, lambda x, y: (recs[x][0] > recs[y][0]) - (recs[x][0] < recs[y][0]))
        self.assertEqual([recs[i][0] for i in idx], sorted(r[0] for r in recs))
        # the permutation is fixed by the algorithm (pinned from tools/link.py's verified 249/249 ICF model: not stable)
        self.assertNotEqual(idx, sorted(range(30), key=lambda i: recs[i][0]))


if __name__ == "__main__":
    unittest.main()
