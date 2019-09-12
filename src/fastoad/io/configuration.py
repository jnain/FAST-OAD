"""
Module for building OpenMDAO problem from configuration file
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
import os.path as pth
from typing import Union

import openmdao.api as om
import toml

from fastoad.io.xml import OpenMdaoXmlIO
from fastoad.module_management.openmdao_system_factory import OpenMDAOSystemFactory

# Logger for this module

_LOGGER = logging.getLogger(__name__)

KEY_FOLDERS = 'module_folders'
KEY_INPUT_FILE = 'input_file'
KEY_OUTPUT_FILE = 'output_file'
KEY_COMPONENT_ID = 'id'
TABLE_PROBLEM = 'problem'
TABLES_DESIGN_VAR = 'design_var'
TABLES_OBJECTIVE = 'objective'
TABLES_CONSTRAINT = 'constraint'


class ConfiguredProblem(om.Problem):
    """
    Vanilla OpenMDAO Problem except that its definition can be loaded from
    a TOML file.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._toml_dict = {}
        self._input_file = None
        self._output_file = None

    def configure(self, conf_file):
        """
        Reads definition of the current problem in given file.

        :param conf_file: Path to the file to open or a file descriptor
        """
        # Dev note: toml.load would also accept an array of files as input, but
        # it does not look useful for us, so it is not mentioned in docstring.

        conf_dirname = pth.dirname(pth.abspath(conf_file))  # for resolving relative paths
        self._toml_dict = toml.load(conf_file)

        # I/O files
        input_file = self._toml_dict.get(KEY_INPUT_FILE)
        if input_file:
            self._input_file = pth.join(conf_dirname, input_file)

        output_file = self._toml_dict.get(KEY_OUTPUT_FILE)
        if output_file:
            self._output_file = pth.join(conf_dirname, output_file)

        # Looking for modules to register
        module_folder_paths = self._toml_dict.get(KEY_FOLDERS, [])
        for folder_path in module_folder_paths:
            folder_path = pth.join(conf_dirname, folder_path)
            if not pth.exists(folder_path):
                _LOGGER.warning('SKIPPED %s: it does not exist.')
            else:
                OpenMDAOSystemFactory.explore_folder(folder_path)

        # Read problem definition
        problem_definition = self._toml_dict.get(TABLE_PROBLEM)
        if not problem_definition:
            raise FASTConfigurationNoProblemDefined("Section [%s] is missing" % TABLE_PROBLEM)

        try:
            self._parse_problem_table(self, TABLE_PROBLEM, problem_definition)
        except FASTConfigurationBaseKeyBuildingError as err:
            log_err = err.__class__(err, TABLE_PROBLEM)
            _LOGGER.error(log_err)
            raise log_err

        # Objectives
        objective_tables = self._toml_dict.get(TABLES_OBJECTIVE, [])
        for objective_table in objective_tables:
            self.model.add_objective(**objective_table)

        # Constraints
        constraint_tables = self._toml_dict.get(TABLES_CONSTRAINT, [])
        for constraint_table in constraint_tables:
            self.model.add_constraint(**constraint_table)

        self.setup()

    def write_needed_inputs(self):
        if self._input_file:
            print(self._input_file)
            writer = OpenMdaoXmlIO(self._input_file)
            writer.write_inputs(self)

    def read_inputs(self):
        if self._input_file:
            reader = OpenMdaoXmlIO(self._input_file)
            self.model.add_subsystem('inputs', reader.read(), promotes=['*'])

            # Design variables
            design_var_tables = self._toml_dict.get(TABLES_DESIGN_VAR, [])
            for design_var_table in design_var_tables:
                self.model.add_design_var(**design_var_table)

            self.setup()

    def write_outputs(self):
        if self._output_file:
            writer = OpenMdaoXmlIO(self._output_file)
            writer.write(self.model)

    def _parse_problem_table(self, component: Union[om.Problem, om.Group], identifier, table: dict):
        """
        Feeds provided *component*, associated to provided *identifier*, using definition
        in provided TOML *table*.

        :param component:
        :param identifier:
        :param table:
        """
        assert isinstance(table, dict), "table should be a dictionary"

        if identifier == TABLE_PROBLEM:  # component is a Problem
            group = component.model
        else:  # component is a Group
            assert isinstance(component, om.Group)
            group = component

        # Assessing sub-components
        if KEY_COMPONENT_ID in table:  # table defines a non-Group component
            sub_component = OpenMDAOSystemFactory.get_system(table[KEY_COMPONENT_ID])
            group.add_subsystem(identifier, sub_component, promotes=['*'])
        else:
            for key, value in table.items():
                if isinstance(value, dict):  # value defines a sub-component
                    sub_component = group.add_subsystem(key, om.Group(), promotes=['*'])
                    try:
                        self._parse_problem_table(sub_component, key, value)
                    except FASTConfigurationBadOpenMDAOInstructionError as err:
                        # There has been an error while parsing an attribute.
                        # Error is relayed with key added for context
                        raise FASTConfigurationBadOpenMDAOInstructionError(err, key)
                else:
                    # value is an attribute of current component and will be literally interpreted
                    try:
                        # FIXME: maybe there is a better way to do that
                        setattr(component, key, eval(value))  # pylint:disable=eval-used
                    except Exception as err:
                        raise FASTConfigurationBadOpenMDAOInstructionError(err, key, value)

        return component


class FASTConfigurationBaseKeyBuildingError(Exception):
    """
    Class for being raised from bottom to top of TOML dict so that in the end, the message
    provides the full qualified name of the problematic key.

    using `new_err = FASTConfigurationBaseKeyBuilding(err, 'new_err_key', <value>)`:

    - if err is a FASTConfigurationBaseKeyBuilding instance with err.key=='err_key':
        - new_err.key will be 'new_err_key.err_key'
        - new_err.value will be err.value (no need to provide a value here)
        - new_err.original_exception will be err.original_exception
    - otherwise, new_err.key will be 'new_err_key' and new_err.value will be <value>
        - new_err.key will be 'new_err_key'
        - new_err.value will be <value>
        - new_err.original_exception will be err

    :param original_exception: the error that happened for raising this one
    :param key: the current key
    :param value: the current value
    """

    def __init__(self, original_exception: Exception, key: str, value=None):
        """ Constructor """

        self.key = None
        """
        the "qualified key" (like "problem.group.component1") related to error, build
        through raising up the error
        """

        self.value = None
        """ the value related to error """

        self.original_exception = None
        """ the original error, when eval failed """

        if hasattr(original_exception, 'key'):
            self.key = '%s.%s' % (key, original_exception.key)
        else:
            self.key = key
        if hasattr(original_exception, 'value'):
            self.value = '%s.%s' % (value, original_exception.value)
        else:
            self.value = value
        if hasattr(original_exception, 'original_exception'):
            self.original_exception = original_exception.original_exception
        else:
            self.original_exception = original_exception
        super().__init__(self, 'Attribute or value not recognized : %s = "%s"\nOriginal error: %s' %
                         (self.key, self.value, self.original_exception))


class FASTConfigurationBadOpenMDAOInstructionError(FASTConfigurationBaseKeyBuildingError):
    """ Class for managing errors that result from trying to set an attribute by eval."""


class FASTConfigurationNoProblemDefined(Exception):
    """Raised if no problem definition found in configuration file"""
