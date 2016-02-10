
from twisted.trial import unittest

from epsilon.modal import mode, Modal

class ModalTestClass(Modal):

    modeAttribute = 'mode'
    initialMode = 'alpha'

    class alpha(mode):
        def one(self):
            return 'alpha-one'
        def two(self):
            return 'alpha-two'

    class beta(mode):
        def two(self):
            return 'beta-two'
        def three(self):
            return 'beta-three'

    def four(self):
        return 'unmode-four'

    class gamma(mode):
        def change(self):
            self.mode = 'delta'
            return self.change()

    class delta(mode):
        def change(self):
            return 'delta-change'

class ModalTestSubclass(ModalTestClass):
    pass

class ModalityTestCase(unittest.TestCase):
    modalFactory = ModalTestClass
    def testModalMethods(self):
        x = self.modalFactory()
        self.assertEqual(x.one(), 'alpha-one')
        self.assertEqual(x.two(), 'alpha-two')
        self.assertRaises(AttributeError, getattr, x, 'three')
        self.assertEqual(x.four(), 'unmode-four')

        x.mode = 'beta'
        self.assertRaises(AttributeError, getattr, x, 'one')
        self.assertEqual(x.two(), 'beta-two')
        self.assertEqual(x.three(), 'beta-three')
        self.assertEqual(x.four(), 'unmode-four')

    def testInternalModeChange(self):
        x = self.modalFactory()
        x.mode = 'gamma'
        self.assertEqual(x.change(), 'delta-change')


class MostBasicInheritanceTestCase(ModalityTestCase):
    modalFactory = ModalTestSubclass
