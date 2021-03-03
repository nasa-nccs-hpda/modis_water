
import unittest

from modis_water.model.SimpleClassifier import SimpleClassifier


# -----------------------------------------------------------------------------
# class SimpleClassifierTestCase
#
# python -m unittest discover model/tests/
# python -m unittest modis_water.model.tests.test_SimpleClassifier
# -----------------------------------------------------------------------------
class SimpleClassifierTestCase(unittest.TestCase):

    # -------------------------------------------------------------------------
    # testInit
    # -------------------------------------------------------------------------
    def testInit(self):
        
        sc = SimpleClassifier()

