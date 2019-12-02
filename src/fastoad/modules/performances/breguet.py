"""
Simple module for performances
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
import openmdao.api as om
from scipy.constants import g

from fastoad.constants import FlightPhase
from fastoad.utils.physics import Atmosphere

CLIMB_RATIO = 0.97  # = mass at end of climb / mass at start of climb
DESCENT_RATIO = 0.98  # = mass at end of descent / mass at start of descent
RESERVE_RATIO = 1.06
CLIMB_DESCENT_DISTANCE = 500  # in km, distance of climb + descent


class BreguetFromMTOW(om.Group):
    """
    Estimation of fuel consumption through Breguet formula with a rough estimate
    of climb and descent phases. MTOW is an input.
    """

    def setup(self):
        self.add_subsystem('propulsion', _BreguetPropulsion(), promotes=['*'])
        self.add_subsystem('distances', _Distances(), promotes=['*'])
        self.add_subsystem('cruise_mass_ratio', _CruiseMassRatio(), promotes=['*'])
        self.add_subsystem('fuel_weights', _FuelWeightFromMTOW(), promotes=['*'])


class BreguetFromOWE(om.Group):
    """
    Estimation of fuel consumption through Breguet formula with a rough estimate
    of climb and descent phases. OWE is an input, MTOW is an output.
    """

    def setup(self):
        self.add_subsystem('propulsion', _BreguetPropulsion(), promotes=['*'])
        self.add_subsystem('distances', _Distances(), promotes=['*'])
        self.add_subsystem('cruise_mass_ratio', _CruiseMassRatio(), promotes=['*'])
        self.add_subsystem('breguet', _MTOWFromOWE(), promotes=['*'])
        self.add_subsystem('fuel_weights', _FuelWeightFromMTOW(), promotes=['*'])

        self.nonlinear_solver = om.NewtonSolver()
        self.linear_solver = om.DirectSolver()


class _BreguetPropulsion(om.ExplicitComponent):
    """
    Link with engine computation
    """

    def setup(self):
        self.add_input('sizing_mission:mission:operational:cruise:altitude', np.nan, units='m')
        self.add_input('TLAR:cruise_mach', np.nan)
        self.add_input('weight:aircraft:MTOW', np.nan, units='kg')
        self.add_input('aerodynamics:aircraft:cruise:L_D_max', np.nan)
        self.add_input('geometry:propulsion:engine:count', 2)

        self.add_output('propulsion:phase', FlightPhase.CRUISE)
        self.add_output('propulsion:use_thrust_rate', False)
        self.add_output('propulsion:required_thrust_rate', 0.)
        self.add_output('propulsion:required_thrust', units='N')
        self.add_output('propulsion:altitude', units='m')
        self.add_output('propulsion:mach')

        self.declare_partials('propulsion:phase', '*', method='fd')
        self.declare_partials('propulsion:use_thrust_rate', '*', method='fd')
        self.declare_partials('propulsion:required_thrust_rate', '*', method='fd')
        self.declare_partials('propulsion:required_thrust', '*', method='fd')
        self.declare_partials('propulsion:altitude',
                              'sizing_mission:mission:operational:cruise:altitude', method='fd')
        self.declare_partials('propulsion:mach', 'TLAR:cruise_mach', method='fd')

    def compute(self, inputs, outputs, discrete_inputs=None, discrete_outputs=None):
        engine_count = inputs['geometry:propulsion:engine:count']
        ld_ratio = inputs['aerodynamics:aircraft:cruise:L_D_max']
        mtow = inputs['weight:aircraft:MTOW']
        initial_cruise_mass = mtow * CLIMB_RATIO

        # Variables for propulsion
        outputs['propulsion:altitude'] = inputs[
            'sizing_mission:mission:operational:cruise:altitude']
        outputs['propulsion:mach'] = inputs['TLAR:cruise_mach']

        outputs['propulsion:required_thrust'] = initial_cruise_mass / ld_ratio * g / engine_count


class _FuelWeightFromMTOW(om.ExplicitComponent):
    """
    Estimation of fuel consumption through Breguet formula with a rough estimate
    of climb and descent phases
    """

    def setup(self):
        self.add_input('TLAR:cruise_mach', np.nan)
        self.add_input('TLAR:range', np.nan, units='m')
        self.add_input('aerodynamics:aircraft:cruise:L_D_max', np.nan)
        self.add_input('propulsion:SFC', np.nan, units='kg/N/s')
        self.add_input('weight:aircraft:MTOW', np.nan, units='kg')
        self.add_input('sizing_mission:mission:operational:cruise:mass_ratio', np.nan)
        self.add_input('sizing_mission:mission:operational:cruise:altitude', np.nan, units='m')

        self.add_output('sizing_mission:mission:operational:ZFW', units='kg')
        self.add_output('sizing_mission:mission:operational:mission:fuel', units='kg')
        self.add_output('sizing_mission:mission:operational:flight:fuel', units='kg')
        self.add_output('sizing_mission:mission:operational:climb:fuel', units='kg')
        self.add_output('sizing_mission:mission:operational:cruise:fuel', units='kg')
        self.add_output('sizing_mission:mission:operational:descent:fuel', units='kg')
        self.add_output('sizing_mission:mission:operational:fuel_reserve', units='kg')

        self.declare_partials('sizing_mission:mission:operational:ZFW', '*', method='fd')
        self.declare_partials('sizing_mission:mission:operational:mission:fuel', '*', method='fd')
        self.declare_partials('sizing_mission:mission:operational:flight:fuel', '*', method='fd')
        self.declare_partials('sizing_mission:mission:operational:climb:fuel', '*', method='fd')
        self.declare_partials('sizing_mission:mission:operational:cruise:fuel', '*', method='fd')
        self.declare_partials('sizing_mission:mission:operational:descent:fuel', '*', method='fd')
        self.declare_partials('sizing_mission:mission:operational:fuel_reserve', '*', method='fd')

    def compute(self, inputs, outputs, discrete_inputs=None, discrete_outputs=None):
        mtow = inputs['weight:aircraft:MTOW']
        cruise_mass_ratio = inputs['sizing_mission:mission:operational:cruise:mass_ratio']

        flight_mass_ratio = cruise_mass_ratio * CLIMB_RATIO * DESCENT_RATIO
        zfw = mtow * flight_mass_ratio / RESERVE_RATIO
        mission_fuel = mtow - zfw

        outputs['sizing_mission:mission:operational:ZFW'] = zfw

        outputs['sizing_mission:mission:operational:mission:fuel'] = mission_fuel
        outputs['sizing_mission:mission:operational:flight:fuel'] = mtow * (1. - flight_mass_ratio)
        outputs['sizing_mission:mission:operational:climb:fuel'] = mtow * (1. - CLIMB_RATIO)
        outputs['sizing_mission:mission:operational:cruise:fuel'] = \
            mtow * CLIMB_RATIO * (1. - cruise_mass_ratio)
        outputs['sizing_mission:mission:operational:descent:fuel'] = \
            mtow * CLIMB_RATIO * cruise_mass_ratio*(1. - DESCENT_RATIO)
        outputs['sizing_mission:mission:operational:fuel_reserve'] = zfw * (RESERVE_RATIO - 1.)


class _MTOWFromOWE(om.ImplicitComponent):
    """
    Estimation of fuel consumption through Breguet formula with a rough estimate
    of climb and descent phases
    """

    def setup(self):
        self.add_input('sizing_mission:mission:operational:cruise:mass_ratio', np.nan)
        self.add_input('TLAR:range', np.nan, units='m')
        self.add_input('weight:aircraft:OWE', np.nan, units='kg')
        self.add_input('weight:aircraft:payload', np.nan, units='kg')

        self.add_output('weight:aircraft:MTOW', units='kg', ref=100000)

        self.declare_partials('weight:aircraft:MTOW', '*', method='fd')

    def apply_nonlinear(self, inputs, outputs, residuals):
        owe = inputs['weight:aircraft:OWE']
        payload_weight = inputs['weight:aircraft:payload']
        cruise_mass_ratio = inputs['sizing_mission:mission:operational:cruise:mass_ratio']

        mtow = outputs['weight:aircraft:MTOW']

        flight_mass_ratio = cruise_mass_ratio * CLIMB_RATIO * DESCENT_RATIO
        zfw = mtow * flight_mass_ratio / RESERVE_RATIO
        mission_owe = zfw - payload_weight

        residuals['weight:aircraft:MTOW'] = owe - mission_owe

    def guess_nonlinear(self, inputs, outputs, residuals,
                        discrete_inputs=None, discrete_outputs=None):
        # pylint: disable=too-many-arguments # It's OpenMDAO's fault :)
        outputs['weight:aircraft:MTOW'] = inputs['weight:aircraft:OWE'] * 1.5


class _Distances(om.ExplicitComponent):
    """ Rough estimation of distances for each flight phase"""

    def setup(self):
        self.add_input('TLAR:range', np.nan, units='m')

        self.add_output('sizing_mission:mission:operational:climb:distance', units='m')
        self.add_output('sizing_mission:mission:operational:cruise:distance', units='m')
        self.add_output('sizing_mission:mission:operational:descent:distance', units='m')

    def compute(self, inputs, outputs, discrete_inputs=None, discrete_outputs=None):
        flight_range = inputs['TLAR:range']

        outputs['sizing_mission:mission:operational:cruise:distance'] = \
            flight_range - CLIMB_DESCENT_DISTANCE * 1000.
        outputs['sizing_mission:mission:operational:climb:distance'] = \
            CLIMB_DESCENT_DISTANCE * 500.
        outputs['sizing_mission:mission:operational:descent:distance'] = \
            CLIMB_DESCENT_DISTANCE * 500.


class _CruiseMassRatio(om.ExplicitComponent):
    """
    Estimation of fuel consumption through Breguet formula for a given cruise distance
    """

    def setup(self):
        self.add_input('aerodynamics:aircraft:cruise:L_D_max', np.nan)
        self.add_input('propulsion:SFC', 1e-5, units='kg/N/s')
        self.add_input('TLAR:cruise_mach', np.nan)
        self.add_input('sizing_mission:mission:operational:cruise:altitude', np.nan, units='m')
        self.add_input('sizing_mission:mission:operational:cruise:distance', np.nan, units='m')

        self.add_output('sizing_mission:mission:operational:cruise:mass_ratio')

        self.declare_partials('sizing_mission:mission:operational:cruise:mass_ratio', '*',
                              method='fd')

    def compute(self, inputs, outputs, discrete_inputs=None, discrete_outputs=None):
        atmosphere = Atmosphere(inputs['sizing_mission:mission:operational:cruise:altitude'],
                                altitude_in_feet=False)
        cruise_speed = atmosphere.speed_of_sound * inputs['TLAR:cruise_mach']

        cruise_distance = inputs['sizing_mission:mission:operational:cruise:distance']
        ld_ratio = inputs['aerodynamics:aircraft:cruise:L_D_max']
        sfc = inputs['propulsion:SFC']

        range_factor = cruise_speed * ld_ratio / g / sfc
        # During first iterations, SFC will be incorrect and range_factor may be too low,
        # resulting in null or too small cruise_mass_ratio.
        # Forcing cruise_mass_ratio to a minimum of 0.3 avoids problems and should not
        # harm (no airplane loses 70% of its weight from fuel consumption)
        cruise_mass_ratio = np.maximum(0.3, 1. / np.exp(cruise_distance / range_factor))

        outputs['sizing_mission:mission:operational:cruise:mass_ratio'] = cruise_mass_ratio
