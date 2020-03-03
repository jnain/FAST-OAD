"""
Estimation of cargo configuration weight
"""

#  This file is part of FAST : A framework for rapid Overall Aircraft Design
#  Copyright (C) 2020  ONERA/ISAE
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

from fastoad.modules.options import AIRCRAFT_TYPE_OPTION


class CargoConfigurationWeight(ExplicitComponent):
    # TODO: Document equations. Cite sources
    """ Cargo configuration weight estimation (D1) """

    def initialize(self):
        self.options.declare(AIRCRAFT_TYPE_OPTION, types=float, default=2.0)

    def setup(self):
        self.add_input('data:geometry:cabin:NPAX1', val=np.nan)
        self.add_input('data:geometry:cabin:containers:count', val=np.nan)
        self.add_input('data:geometry:cabin:pallet_count', val=np.nan)
        self.add_input('data:geometry:cabin:seats:economical:count_by_row', val=np.nan)
        self.add_input('tuning:weight:furniture:cargo_configuration:mass:k', val=1.)
        self.add_input('tuning:weight:furniture:cargo_configuration:mass:offset', val=0.,
                       units='kg')

        self.add_output('data:weight:furniture:cargo_configuration:mass', units='kg')

    def compute(self, inputs, outputs
                , discrete_inputs=None, discrete_outputs=None):
        npax1 = inputs['data:geometry:cabin:NPAX1']
        side_by_side_eco_seat_count = inputs['data:geometry:cabin:seats:economical:count_by_row']
        container_count = inputs['data:geometry:cabin:containers:count']
        pallet_number = inputs['data:geometry:cabin:pallet_count']
        k_d1 = inputs['tuning:weight:furniture:cargo_configuration:mass:k']
        offset_d1 = inputs['tuning:weight:furniture:cargo_configuration:mass:offset']

        if self.options[AIRCRAFT_TYPE_OPTION] == 6.0:
            if side_by_side_eco_seat_count <= 6.0:
                temp_d1 = 0.351 * (npax1 - 38)
            else:
                temp_d1 = 85 * container_count + 110 * pallet_number
            outputs['data:weight:furniture:cargo_configuration:mass'] = k_d1 * temp_d1 + offset_d1
        else:
            outputs['data:weight:furniture:cargo_configuration:mass'] = 0.