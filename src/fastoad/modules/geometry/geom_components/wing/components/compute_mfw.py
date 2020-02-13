"""
    Estimation of max fuel weight
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
import numpy as np
from openmdao.core.explicitcomponent import ExplicitComponent

# TODO: This belongs more to mass breakdown than geometry
class ComputeMFW(ExplicitComponent):
    # TODO: Document equations. Cite sources
    """ Max fuel weight estimation """

    def setup(self):

        self.add_input('geometry:wing:area', val=np.nan, units='m**2')
        self.add_input('geometry:wing:aspect_ratio', val=np.nan)
        self.add_input('geometry:wing:root:thickness_ratio', val=np.nan)
        self.add_input('geometry:wing:tip:thickness_ratio', val=np.nan)

        self.add_output('weight:aircraft:MFW', units='kg')

        self.declare_partials('weight:aircraft:MFW', '*', method='fd')

    def compute(self, inputs, outputs):
        wing_area = inputs['geometry:wing:area']
        lambda_wing = inputs['geometry:wing:aspect_ratio']
        el_emp = inputs['geometry:wing:root:thickness_ratio']
        el_ext = inputs['geometry:wing:tip:thickness_ratio']

        # TODO: remove hard coded value
        mfw = 224 * (wing_area ** 1.5 * lambda_wing ** (-0.4)
                     * (0.6 * el_emp + 0.4 * el_ext)) + 1570

        outputs['weight:aircraft:MFW'] = mfw