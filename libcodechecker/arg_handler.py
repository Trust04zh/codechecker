# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle old-style subcommand invocation.
"""
import os
import socket
import sys

from libcodechecker import client
from libcodechecker import debug_reporter
from libcodechecker import generic_package_context
from libcodechecker import host_check
from libcodechecker import util
from libcodechecker.analyze import analyzer_env
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.database_handler import SQLServer
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('ARG_HANDLER')


# TODO: Will be replaced wholly by libcodechecker/checkers.py.
def handle_list_checkers(args):
    """
    List the supported checkers by the analyzers.
    List the default enabled and disabled checkers in the config.
    """
    context = generic_package_context.get_context()
    # If nothing is set, list checkers for all supported analyzers.
    analyzers = args.analyzers or analyzer_types.supported_analyzers
    enabled_analyzers, _ = analyzer_types\
        .check_supported_analyzers(analyzers, context)
    analyzer_environment = analyzer_env.get_check_env(
        context.path_env_extra,
        context.ld_lib_path_extra)

    for ea in enabled_analyzers:
        if ea not in analyzer_types.supported_analyzers:
            LOG.error('Unsupported analyzer ' + str(ea))
            sys.exit(1)

    analyzer_config_map = \
        analyzer_types.build_config_handlers(args,
                                             context,
                                             enabled_analyzers)

    for ea in enabled_analyzers:
        # Get the config.
        config_handler = analyzer_config_map.get(ea)
        source_analyzer = \
            analyzer_types.construct_analyzer_type(ea,
                                                   config_handler,
                                                   None)

        checkers = source_analyzer.get_analyzer_checkers(config_handler,
                                                         analyzer_environment)

        default_checker_cfg = context.default_checkers_config.get(
            ea + '_checkers')

        analyzer_types.initialize_checkers(config_handler,
                                           checkers,
                                           default_checker_cfg)
        for checker_name, value in config_handler.checks().items():
            enabled, description = value
            if enabled:
                print(' + {0:50} {1}'.format(checker_name, description))
            else:
                print(' - {0:50} {1}'.format(checker_name, description))


def handle_debug(args):
    """
    Runs a debug command on the buildactions where the analysis
    failed for some reason.
    """
    context = generic_package_context.get_context()

    context.codechecker_workspace = args.workspace
    context.db_username = args.dbusername

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    sql_server = SQLServer.from_cmdline_args(args,
                                             context.migration_root,
                                             check_env)
    sql_server.start(context.db_version_info, wait_for_start=True, init=False)

    debug_reporter.debug(context, sql_server.get_connection_string(),
                         args.force)
