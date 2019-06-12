"""
This module launches XFOIL computations
"""
#  This file is part of FAST : A framework for rapid Overall Aircraft Design
#  Copyright (C) 2019  ONERA/ISAE
#  FAST is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import logging
import os
import os.path as pth

import numpy as np

from fastoad.modules.aerodynamics.xfoil.xfoil_computation import XfoilInputFileGenerator
from . import XfoilComputation

_INPUT_FILE_NAME = 'point_input.txt'

_LOGGER = logging.getLogger(__name__)


class XfoilPoint(XfoilComputation):
    """
    Runs a point computation with XFOIL and returns the max lift coefficient
    """

    def setup(self):
        super(XfoilPoint, self).setup()
        self.options['input_file_generator'] = PointIFG()
        self.add_input('profile:alpha', val=np.nan)


class PointIFG(XfoilInputFileGenerator):

    def get_template(self):
        return pth.join(os.path.dirname(__file__), _INPUT_FILE_NAME)

    def transfer_vars(self):
        if self.inputs is None:
            raise AttributeError("self.inputs should be defined.")
        self.mark_anchor('RE')
        self.transfer_var(self.inputs['profile:reynolds'], 1, 1)
        self.mark_anchor('M')
        self.transfer_var(self.inputs['profile:mach'], 1, 1)
        self.mark_anchor('ALFA')
        self.transfer_var(self.inputs['profile:alpha'], 1, 1)

    def __init__(self):
        super(PointIFG, self).__init__()
        self.inputs: dict = None

    def generate(self, return_data=False):
        super(PointIFG, self).generate()
