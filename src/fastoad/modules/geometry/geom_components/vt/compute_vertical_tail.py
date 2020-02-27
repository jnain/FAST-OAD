"""
    Estimation of geometry of vertical tail
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


from fastoad.modules.geometry.geom_components.fuselage import ComputeCnBetaFuselage
from fastoad.modules.geometry.geom_components.vt.components import ComputeVTChords
from fastoad.modules.geometry.geom_components.vt.components import ComputeVTClalpha
from fastoad.modules.geometry.geom_components.vt.components import ComputeVTDistance
from fastoad.modules.geometry.geom_components.vt.components import ComputeVTMAC
from fastoad.modules.geometry.geom_components.vt.components import ComputeVTSweep
from fastoad.modules.geometry.geom_components.vt.components import ComputeVTVolCoeff
from fastoad.modules.handling_qualities.compute_vt_area import ComputeVTArea
from fastoad.modules.options import TAIL_TYPE_OPTION, AIRCRAFT_FAMILY_OPTION, \
    OpenMdaoOptionDispatcherGroup


class ComputeVerticalTailGeometry(OpenMdaoOptionDispatcherGroup):
    """ Vertical tail geometry estimation """

    def initialize(self):
        self.options.declare(TAIL_TYPE_OPTION, types=float, default=0.)
        self.options.declare(AIRCRAFT_FAMILY_OPTION, types=float, default=1.0)

    def setup(self):
        self.add_subsystem('fuselage_cnbeta', ComputeCnBetaFuselage(), promotes=['*'])
        self.add_subsystem('vt_aspect_ratio', ComputeVTDistance(), promotes=['*'])
        self.add_subsystem('vt_clalpha', ComputeVTClalpha(), promotes=['*'])
        self.add_subsystem('vt_area', ComputeVTArea(), promotes=['*'])
        self.add_subsystem('vt_vol_coeff', ComputeVTVolCoeff(), promotes=['*'])
        self.add_subsystem('vt_chords', ComputeVTChords(), promotes=['*'])
        self.add_subsystem('vt_mac', ComputeVTMAC(), promotes=['*'])
        self.add_subsystem('vt_sweep', ComputeVTSweep(), promotes=['*'])
