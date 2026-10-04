from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from execution_linear_reference import fit_reference


class LinearReferenceTests(unittest.TestCase):
    def test_reserved_labels_cannot_change_fit_calibration_or_forecasts(self):
        rng=np.random.default_rng(31)
        x=rng.normal(size=(25,16,24)).astype(np.float32)
        y=rng.integers(0,5,size=(25,3,2,2))
        roles=np.repeat(np.arange(5),5)
        a,pa=fit_reference(x,y,roles)
        changed=y.copy();changed[roles>=2]=(changed[roles>=2]+1)%5
        b,pb=fit_reference(x,changed,roles)
        self.assertEqual(pa,pb)
        self.assertTrue(np.array_equal(a,b))
        self.assertEqual(a.shape,(25,3,2,2,5))
        self.assertTrue(np.isfinite(a).all())
        self.assertTrue(np.allclose(a.sum(axis=-1),1))


if __name__=='__main__':unittest.main()
