
"""
Tests for L{epsilon.structlike}.
"""

import threading

from epsilon.structlike import record
from twisted.internet import reactor
from twisted.internet.defer import gatherResults
from twisted.internet.threads import deferToThreadPool
from twisted.python.threadpool import ThreadPool
from twisted.trial import unittest


class MyRecord(record('something somethingElse')):
    """
    A sample record subclass.
    """



class StructLike(unittest.TestCase):
    def _testme(self, TestStruct):
        x = TestStruct()
        self.assertEqual(x.x, 1)
        self.assertEqual(x.y, 2)
        self.assertEqual(x.z, 3)

        y = TestStruct('3', '2', '1')
        self.assertEqual(y.x, '3')
        self.assertEqual(y.y, '2')
        self.assertEqual(y.z, '1')

        z = TestStruct(z='z', x='x', y='y')
        self.assertEqual(z.x, 'x')
        self.assertEqual(z.y, 'y')
        self.assertEqual(z.z, 'z')

        a = TestStruct('abc')
        self.assertEqual(a.x, 'abc')
        self.assertEqual(a.y, 2)
        self.assertEqual(a.z, 3)

        b = TestStruct(y='123')
        self.assertEqual(b.x, 1)
        self.assertEqual(b.y, '123')
        self.assertEqual(b.z, 3)

    def testWithPositional(self):
        self._testme(record('x y z', x=1, y=2, z=3))

    def testWithPositionalSubclass(self):
        class RecordSubclass(record('x y z', x=1, y=2, z=3)):
            pass
        self._testme(RecordSubclass)

    def testWithoutPositional(self):
        self._testme(record(x=1, y=2, z=3))

    def testWithoutPositionalSubclass(self):
        class RecordSubclass(record(x=1, y=2, z=3)):
            pass
        self._testme(RecordSubclass)

    def testBreakRecord(self):
        self.assertRaises(TypeError, record)
        self.assertRaises(TypeError, record, 'a b c', a=1, c=2)
        self.assertRaises(TypeError, record, 'a b', c=2)
        self.assertRaises(TypeError, record, 'a b', a=1)

    def testUndeclared(self):
        R = record('a')
        r = R(1)
        r.foo = 2
        self.assertEqual(r.foo, 2)

    def testCreateWithNoValuesAndNoDefaults(self):
        R = record('x')
        self.assertRaises(TypeError, R)

    def testUnknownArgs(self):
        """
        Test that passing in unknown keyword and / or positional arguments to a
        record's initializer causes TypeError to be raised.
        """
        R = record('x')
        self.assertRaises(TypeError, R, x=5, y=6)
        self.assertRaises(TypeError, R, 5, 6)


    def test_typeStringRepresentation(self):
        """
        'Record' types should have a name which provides information about the
        slots they contain.
        """
        R = record('xyz abc def')
        self.assertEqual(R.__name__, "Record<xyz abc def>")


    def test_instanceStringRepresentation(self):
        """
        'Record' instances should provide a string representation which
        provides information about the values contained in their slots.
        """
        obj = MyRecord(something=1, somethingElse=2)
        self.assertEqual(repr(obj), 'MyRecord(something=1, somethingElse=2)')


    def test_instanceStringRepresentationNesting(self):
        """
        Nested L{Record} instances should have nested string representations.
        """
        obj = MyRecord(something=1, somethingElse=2)
        objRepr = 'MyRecord(something=1, somethingElse=2)'
        self.assertEqual(
            repr(MyRecord(obj, obj)),
            'MyRecord(something=%s, somethingElse=%s)' % (objRepr, objRepr))


    def test_instanceStringRepresentationRecursion(self):
        """
        'Record' instances should provide a repr that displays 'ClassName(...)'
        when it would otherwise infinitely recurse.
        """
        obj = MyRecord(something=1, somethingElse=2)
        obj.somethingElse = obj
        self.assertEqual(
            repr(obj), 'MyRecord(something=1, somethingElse=MyRecord(...))')


    def test_instanceStringRepresentationUnhashableRecursion(self):
        """
        'Record' instances should display 'ClassName(...)' even for unhashable
        objects.
        """
        obj = MyRecord(something=1, somethingElse=[])
        obj.somethingElse.append(obj)
        self.assertEqual(
            repr(obj), 'MyRecord(something=1, somethingElse=[MyRecord(...)])')


    def test_threadLocality(self):
        """
        An 'Record' repr()'d in two separate threads at the same time should
        look the same (i.e. the repr state tracking for '...' should be
        thread-local).
        """
        pool = ThreadPool(2, 2)
        pool.start()
        self.addCleanup(pool.stop)

        class StickyRepr(object):
            """
            This has a __repr__ which will block until a separate thread
            notifies it that it should return.  We use this to create a race
            condition.
            """
            waited = False
            def __init__(self):
                self.set = threading.Event()
                self.wait = threading.Event()
            def __repr__(self):
                if not self.waited:
                    self.set.set()
                    self.wait.wait()
                return 'sticky'
        r = StickyRepr()
        mr = MyRecord(something=1, somethingElse=r)
        d = deferToThreadPool(reactor, pool, repr, mr)
        def otherRepr():
            # First we wait for the first thread doing a repr() to enter its
            # __repr__()...
            r.set.wait()
            # OK, now it's blocked.  Let's make sure that subsequent calls to
            # this repr() won't block.
            r.waited = True
            # Do it!  This is a concurrent repr().
            result = repr(mr)
            # Now we're done, wake up the other repr and let it complete.
            r.wait.set()
            return result
        d2 = deferToThreadPool(reactor, pool, otherRepr)

        def done(xxx_todo_changeme):
            (thread1repr, thread2repr) = xxx_todo_changeme
            knownGood = 'MyRecord(something=1, somethingElse=sticky)'
            # self.assertEquals(thread1repr, thread2repr)
            self.assertEqual(thread1repr, knownGood)
            self.assertEqual(thread2repr, knownGood)
        return gatherResults([d, d2]).addCallback(done)
