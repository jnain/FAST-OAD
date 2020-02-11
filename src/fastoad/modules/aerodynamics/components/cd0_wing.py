"""
    FAST - Copyright (c) 2016 ONERA ISAE
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

from fastoad.modules.aerodynamics.constants import POLAR_POINT_COUNT


class Cd0Wing(ExplicitComponent):
    def initialize(self):
        self.options.declare('low_speed_aero', default=False, types=bool)

    def setup(self):
        self.low_speed_aero = self.options['low_speed_aero']

        nans_array = np.full(POLAR_POINT_COUNT, np.nan)
        if self.low_speed_aero:
            self.add_input('reynolds_low_speed', val=np.nan)
            self.add_input('cl_low_speed', val=nans_array)
            self.add_input('Mach_low_speed', val=np.nan)
            self.add_output('cd0_wing_low_speed', shape=POLAR_POINT_COUNT)
        else:
            self.add_input('aerodynamics:wing:cruise:reynolds', val=np.nan)
            self.add_input('aerodynamics:aircraft:cruise:CL', val=nans_array)
            self.add_input('TLAR:cruise_mach', val=np.nan)
            self.add_output('aerodynamics:wing:cruise:CD0', shape=POLAR_POINT_COUNT)

        self.add_input('geometry:wing:area', val=np.nan, units='m**2')
        self.add_input('geometry:wing:thickness_ratio', val=np.nan)
        self.add_input('geometry:wing:wetted_area', val=np.nan, units='m**2')
        self.add_input('geometry:wing:MAC:length', val=np.nan, units='m')
        self.add_input('geometry:wing:sweep_25', val=np.nan, units='deg')

        self.declare_partials('*', '*', method='fd')

    def compute(self, inputs, outputs):
        wing_area = inputs['geometry:wing:area']
        wet_area_wing = inputs['geometry:wing:wetted_area']
        el_aero = inputs['geometry:wing:thickness_ratio']
        sweep_25 = inputs['geometry:wing:sweep_25']
        l0_wing = inputs['geometry:wing:MAC:length']
        if self.low_speed_aero:
            cl = inputs['cl_low_speed']
            mach = inputs['Mach_low_speed']
            re_hs = inputs['reynolds_low_speed']
        else:
            cl = inputs['aerodynamics:aircraft:cruise:CL']
            mach = inputs['TLAR:cruise_mach']
            re_hs = inputs['aerodynamics:wing:cruise:reynolds']

        ki_arrow_cd0 = 0.04
        # Friction coefficients
        cf_wing_hs = 0.455 / ((1 + 0.144 * mach ** 2) ** 0.65 * (np.log10(re_hs * l0_wing)) ** 2.58)

        # cd0 wing
        # factor of relative thickness
        ke_cd0_wing = 4.688 * el_aero ** 2 + 3.146 * el_aero
        k_phi_cd0_wing = 1 - 0.000178 * sweep_25 ** 2 - 0.0065 * sweep_25

        kc_cd0_wing = 2.859 * (cl / np.cos(np.radians(sweep_25)) ** 2) ** 3 - \
                      1.849 * (cl / np.cos(np.radians(sweep_25)) ** 2) ** 2 + \
                      0.382 * (cl / np.cos(np.radians(sweep_25)) ** 2) + 0.06  # sweep factor

        cd0_wing = ((ke_cd0_wing + kc_cd0_wing) * k_phi_cd0_wing +
                    ki_arrow_cd0 + 1) * cf_wing_hs * wet_area_wing / wing_area

        if self.low_speed_aero:
            outputs['cd0_wing_low_speed'] = cd0_wing
        else:
            outputs['aerodynamics:wing:cruise:CD0'] = cd0_wing
