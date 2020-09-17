import os
import pandas as pd

class MaskStats(object):
    sourcefile = os.path.join(os.path.join(os.pardir, 'mask-use'), 'mask-use-by-county.csv')
    df = None

    def load(self):
       if self.df is None:
           self.df = pd.read_csv(self.sourcefile)

