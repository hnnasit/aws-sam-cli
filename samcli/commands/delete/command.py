"""
CLI command for "delete" command
"""

import logging

import click
from samcli.cli.main import aws_creds_options, common_options, pass_context, print_cmdline_args

from samcli.lib.utils.version_checker import check_newer_version

SHORT_HELP = "Delete an AWS SAM application and the artifacts created by sam deploy."

HELP_TEXT = """The sam delete command deletes the CloudFormation
stack and all the artifacts which were created using sam deploy.

\b
e.g. sam delete

\b
"""

LOG = logging.getLogger(__name__)


@click.command(
    "delete",
    short_help=SHORT_HELP,
    context_settings={"ignore_unknown_options": False, "allow_interspersed_args": True, "allow_extra_args": True},
    help=HELP_TEXT,
)
@click.option(
    "--stack-name",
    required=False,
    help="The name of the AWS CloudFormation stack you want to delete. ",
)
@click.option(
    "--config-file",
    help=(
        "The path and file name of the configuration file containing default parameter values to use. "
        "Its default value is 'samconfig.toml' in project directory. For more information about configuration files, "
        "see: "
        "https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-config.html."
    ),
    type=click.STRING,
    default="samconfig.toml",
    show_default=True,
)
@click.option(
    "--config-env",
    help=(
        "The environment name specifying the default parameter values in the configuration file to use. "
        "Its default value is 'default'. For more information about configuration files, see: "
        "https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-config.html."
    ),
    type=click.STRING,
    default="default",
    show_default=True,
)
@click.option(
    "--force",
    help=("Specify this flag to allow SAM CLI to skip through the guided prompts" ""),
    is_flag=True,
    type=click.BOOL,
    required=False,
)
@aws_creds_options
@common_options
@pass_context
@check_newer_version
@print_cmdline_args
def cli(ctx, stack_name: str, config_file: str, config_env: str, force: bool):
    """
    `sam delete` command entry point
    """

    # All logic must be implemented in the ``do_cli`` method. This helps with easy unit testing
    do_cli(
        stack_name=stack_name,
        region=ctx.region,
        config_file=config_file,
        config_env=config_env,
        profile=ctx.profile,
        force=force,
    )  # pragma: no cover


def do_cli(stack_name: str, region: str, config_file: str, config_env: str, profile: str, force: bool):
    """
    Implementation of the ``cli`` method
    """
    from samcli.commands.delete.delete_context import DeleteContext

    with DeleteContext(
        stack_name=stack_name,
        region=region,
        profile=profile,
        config_file=config_file,
        config_env=config_env,
        force=force,
    ) as delete_context:
        delete_context.run()
