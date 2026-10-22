"""Differential-harness adversarial controls using authored x86 bodies, not retail payloads.

Run with a Python that has unicorn (requirements.txt); without it the module is skipped. These tests do not compile
the game.
"""
import struct
import unittest

from unittest.mock import patch
from types import SimpleNamespace

e = None    # tools.equiv, imported by setUpModule: it needs unicorn


def setUpModule():
    global e
    try:
        import unicorn  # noqa: F401
    except ImportError:
        raise unittest.SkipTest("equiv_tests needs unicorn (requirements.txt)")
    from tools import equiv
    e = equiv


ENTRY = 0x400100
CALLEE = 0x400800


class Image:
    def __init__(self, code):
        self.data = bytearray(4096)
        self.data[0x100:0x100 + len(code)] = code

    def read(self, address, size):
        off = address - 0x400000
        if off < 0 or off + size > len(self.data):
            return None
        return bytes(self.data[off:off + size])


class ProvenLibraryResolution(unittest.TestCase):
    def test_stale_discovery_cannot_substitute_another_math_entry(self):
        resolver = e.Resolver.__new__(e.Resolver)
        resolver.entry, resolver.stem = ENTRY, 'Authored'
        resolver.by_symbol = {'__CIacos':0x55dcb0, '__CIasin':0x55f380,
                              '__CIfmod':0x55e3e0, '_fmod':0x55e3ea}
        resolver.names = {}
        for section in (0,1,-1):
            for name,expected in [('__CIacos',0x55f380), ('__CIasin',0x55dcb0),
                                  ('_acos',0x55f394), ('_asin',0x55dcc4),
                                  ('__CIfmod',0x55e3ea), ('_fmod',0x55e3e0)]:
                with self.subTest(name=name,section=section):
                    sym = SimpleNamespace(name=name,section=section,value=123,storage=e.SYM_EXTERNAL)
                    self.assertEqual(resolver.resolve(SimpleNamespace(),sym,1), (expected,True))
                    self.assertEqual(resolver.names[expected],name)


    def test_sdk_dispatch_identity_overrides_stale_discovery_and_definition(self):
        entries = [('_D3DXVec3TransformCoord@12', 0x576161),
                   ('_D3DXVec3Project@24', 0x576297),
                   ('_D3DXMatrixMultiply@12', 0x5768fe),
                   ('_D3DXMatrixInverse@12', 0x576e0a),
                   ('_D3DXMatrixTranslation@16', 0x577267)]
        resolver = e.Resolver.__new__(e.Resolver)
        resolver.entry, resolver.stem, resolver.names = ENTRY, 'Authored', {}
        resolver.by_symbol = {name: entries[(i + 1) % len(entries)][1]
                              for i, (name, _) in enumerate(entries)}
        for name, expected in entries:
            for section in (0, 1, -1):
                with self.subTest(name=name, section=section):
                    sym = SimpleNamespace(name=name, section=section, value=123, storage=e.SYM_EXTERNAL)
                    self.assertEqual(resolver.resolve(SimpleNamespace(), sym, 1), (expected, True))



class EmulatorControls(unittest.TestCase):
    def setUp(self):
        self.patches = [patch.object(e, 'HEAP_SIZE', 4096), patch.object(e, 'STACK_SIZE', 65536)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        e.FLOATS.clear()
        e.FOCUS.clear()
        e.INTERESTING.clear()
        e.FLOATY[0] = False

    def run_body(self, code, *, original=None, heap_words=(), sites=None, pop=0, kind='i', extra_pages=()):
        image = Image(code if original is None else original)
        image.data[0x800] = 0xc3
        heap = bytearray(e.HEAP_SIZE)
        for off, value in heap_words:
            heap[off:off + 4] = struct.pack('<I', value)
        pages = [(0x400000, bytes(image.data)), *extra_pages]
        return e.run(image, ENTRY, len(code), code if original is not None else None, 73, b'', e.HEAP,
                     sites or {}, lambda a: pop, lambda a: kind, pages, bytes(heap), 0, 0, lambda a: False, 500)

    def test_indirect_synthetic_base_collision_treated_identically(self):
        # A virtual target that happens to equal the former candidate base must remain an external call in both.
        body = b'\xb8' + struct.pack('<I', 0x60000000) + b'\xff\xd0\xc3'
        extra = ((0x60000000, b'\xc3' + b'\0' * 4095),)
        a = self.run_body(body, extra_pages=extra)
        b = self.run_body(body, original=body, extra_pages=extra)
        self.assertEqual(a['trace'][0][0], 0x60000000)
        self.assertEqual(a['trace'], b['trace'])
        self.assertEqual(a['unsupported'], [])
        self.assertIsNone(e.first_difference(a, b, 'i', {}))

    def test_virtual_recursive_self_call_uses_same_body(self):
        # if (*this) { --*this; this->fn(this); }
        body = b'\x83\x39\x00\x74\x06\x83\x29\x01\xff\x51\x04\xc3'
        args = dict(heap_words=((0, 2), (4, ENTRY)))
        a = self.run_body(body, **args)
        b = self.run_body(body, original=body, **args)
        self.assertEqual(a['trace'], [])
        self.assertEqual(a['writes'][0][e.HEAP], 0)
        self.assertIsNone(e.first_difference(a, b, 'v', {}))

    def test_direct_recursive_self_call_uses_same_body(self):
        body = b'\x83\x39\x00\x74\x08\x83\x29\x01\xe8' + struct.pack('<i', -13) + b'\xc3'
        a = self.run_body(body, heap_words=((0, 3),))
        b = self.run_body(body, original=body, heap_words=((0, 3),))
        self.assertEqual(a['trace'], [])
        self.assertEqual(a['writes'][0][e.HEAP], 0)
        self.assertIsNone(e.first_difference(a, b, 'v', {}))

    def test_float_return_uses_physical_top_register(self):
        a = self.run_body(b'\xd9\xe8\xc3')  # fld1; ret
        b = self.run_body(b'\xd9\xee\xc3', original=b'\xd9\xe8\xc3')  # fldz; ret
        self.assertEqual(a['top'], 7)
        self.assertNotEqual(a['st0'], b['st0'])
        self.assertIsNotNone(e.first_difference(a, b, 'f', {}))

    def test_x87_top_wrap_does_not_hide_eight_leaked_values(self):
        a = self.run_body(b'\xc3')
        b = self.run_body(b'\xd9\xe8' * 8 + b'\xc3')
        self.assertEqual(a['top'], b['top'])
        self.assertNotEqual(a['tags'], b['tags'])
        self.assertIn('occupied', e.first_difference(a, b, 'v', {}))

    def test_stack_pointee_difference_is_not_accepted_as_agreement(self):
        def body(value):
            return (b'\x83\xec\x04\xc7\x04\x24' + struct.pack('<I', value) + b'\x54\xb8' +
                    struct.pack('<I', CALLEE) + b'\xff\xd0\x83\xc4\x04\xc3')
        a = self.run_body(body(1), pop=4)
        b = self.run_body(body(2), pop=4)
        self.assertIn('stack-backed external-call argument is not modeled', a['unsupported'])
        self.assertEqual(a['unsupported'], b['unsupported'])

    def test_reached_trap_with_equal_trace_is_unsupported(self):
        body = b'\xb8' + struct.pack('<I', e.TRAPS) + b'\xff\xd0\xc3'
        a = self.run_body(body)
        self.assertIn('unresolved external call', a['unsupported'])

    def test_delayed_cdecl_cleanup_does_not_hide_arguments(self):
        def body(value):
            return b'\x6a' + bytes([value]) + b'\xb8' + struct.pack('<I', CALLEE) + b'\xff\xd0\x89\xc2\x83\xc4\x04\x31\xc0\xc3'
        args = dict(sites={ENTRY + 9: (4, 0, False)}, pop=0)
        for value in (1, 2):
            run = self.run_body(body(value), **args)
            self.assertIsNone(run['fault'])
            self.assertIn('delayed cdecl argument cleanup is not modeled', run['unsupported'])

    def test_callee_saved_register_clobber_is_observed(self):
        a = self.run_body(b'\xc3')
        b = self.run_body(b'\xbb\x01\x00\x00\x00\xc3')
        self.assertIn('callee-saved', e.first_difference(a, b, 'v', {}))

    def test_floating_point_control_change_is_observed(self):
        a = self.run_body(b'\xc3', heap_words=((0, 0x37f),))
        b = self.run_body(b'\xd9\x29\xc3', heap_words=((0, 0x37f),))
        self.assertIn('control word', e.first_difference(a, b, 'v', {}))

    def test_different_faults_are_not_called_the_same(self):
        a = self.run_body(b'\x0f\x0b')  # ud2
        b = dict(a, fault='different fault')
        self.assertIsNotNone(a['fault'])
        self.assertIn('fault', e.first_difference(a, b, 'v', {}))
        self.assertEqual(e.outcome(0, 1, [], []), 2)

    def test_float_boundary_equality_mutation_is_detected(self):
        # Compare an argument in this[0] against 1.0; the two bodies differ only at JB versus JBE (< versus <=).
        # fld1; fld [ecx]; fcompp; fnstsw ax; sahf; mov eax,0; jb/jbe +5; mov eax,1; ret
        prefix = b'\xd9\xe8\xd9\x01\xde\xd9\xdf\xe0\x9e\xb8\x00\x00\x00\x00'
        left = prefix + b'\x72\x05\xb8\x01\x00\x00\x00\xc3'
        right = prefix + b'\x76\x05\xb8\x01\x00\x00\x00\xc3'
        for bits, same in [(0x3f800000, False), (0x3f800001, True), (0x3f7fffff, True)]:
            a = self.run_body(left, heap_words=((0, bits),))
            b = self.run_body(right, original=left, heap_words=((0, bits),))
            self.assertEqual(e.first_difference(a, b, 'i', {}) is None, same)


class AdmissionControls(unittest.TestCase):
    def test_padding_must_stay_identical_outside_extent(self):
        image = Image(b'\xc3\x90\x90\x90')
        self.assertIsNone(e.overlay_issue(image, ENTRY, 1, b'\xc3\x90\x90\x90'))
        self.assertIsNotNone(e.overlay_issue(image, ENTRY, 1, b'\x90\xc3'))

    def test_no_empty_sample_fault_missing_coverage_or_unresolved_pass(self):
        for args in [(0, 0, [], []), (0, 4, [], []), (4, 1, [], []),
                     (4, 0, [ENTRY], []), (4, 0, [], ['unknown'])]:
            self.assertEqual(e.outcome(*args), 2)
        self.assertEqual(e.outcome(4, 0, [], []), 0)

    def test_stub_return_model_is_compared(self):
        base = dict(fault=None, trace=[(CALLEE, 0, (), 'i')], writes=[{}], eax=0, top=0, tags=0xffff, st0=0, esp=4,
                    preserved=(1, 2, 3, 4), control=0x27f)
        other = dict(base, trace=[(CALLEE, 0, (), 'f')])
        self.assertIn('return model', e.first_difference(base, other, 'v', {}))

    def test_scalar_stubs_reach_flags_and_pointer_stubs_stay_pointers(self):
        values = {e.scalar_return(i, 'i') for i in range(128)}
        self.assertTrue({0, 1, 0xffffffff, 2, 3, 7, 0x80000000} <= values)
        self.assertTrue(all(v == 0 or e.HEAP <= v < e.HEAP + e.HEAP_SIZE
                            for v in (e.scalar_return(i, 'p') for i in range(128))))

    def test_unknown_signature_and_aggregate_size_are_not_guessed(self):
        for name in [None, 'void __fastcall F(int)', 'void __cdecl F(struct Unknown)',
                     'class FVector __thiscall Thing::Get(void)']:
            with self.assertRaises(ValueError):
                e.params(name)


if __name__ == '__main__':
    unittest.main()
