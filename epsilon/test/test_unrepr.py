from twisted.trial import unittest
from epsilon.unrepr import unrepr
class UnreprTestCase(unittest.TestCase):

    def testSimpleUnrepr(self):
        data = {'x': ['bob', (1+2j), []], 10: (1, {}, 'two'), (3, 4): 5}
        self.assertEqual(unrepr(repr(data)), data)
