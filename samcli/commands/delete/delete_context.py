"""
Delete a SAM stack
"""

import boto3


import docker
import click
from click import confirm
from click import prompt
from samcli.cli.cli_config_file import TomlProvider
from samcli.lib.utils.botoconfig import get_boto_config_with_user_agent
from samcli.lib.delete.cf_utils import CfUtils
from samcli.lib.package.s3_uploader import S3Uploader
from samcli.lib.package.artifact_exporter import mktempfile, get_cf_template_name

from samcli.yamlhelper import yaml_parse

from samcli.lib.package.artifact_exporter import Template
from samcli.lib.package.ecr_uploader import ECRUploader
from samcli.lib.package.uploaders import Uploaders

CONFIG_COMMAND = "deploy"
CONFIG_SECTION = "parameters"
TEMPLATE_STAGE = "Original"

class DeleteContext:
    def __init__(self, stack_name: str, region: str, profile: str, config_file: str, config_env: str):
        self.stack_name = stack_name
        self.region = region
        self.profile = profile
        self.config_file = config_file
        self.config_env = config_env
        self.s3_bucket = None
        self.s3_prefix = None
        self.cf_utils = None
        self.s3_uploader = None
        self.uploaders = None
        self.cf_template_file_name = None
        self.delete_artifacts_folder = None
        self.delete_cf_template_file = None

    def __enter__(self):
        self.parse_config_file()
        if not self.stack_name:
            self.stack_name = prompt(
                click.style("\tEnter stack name you want to delete:", bold=True), type=click.STRING
            )

        return self

    def __exit__(self, *args):
        pass

    def parse_config_file(self):
        """
        Read the provided config file if it exists and assign the options values.
        """
        toml_provider = TomlProvider(CONFIG_SECTION, [CONFIG_COMMAND])
        config_options = toml_provider(
            config_path=self.config_file, config_env=self.config_env, cmd_names=[CONFIG_COMMAND]
        )
        if config_options:
            if not self.stack_name:
                self.stack_name = config_options.get("stack_name", None)
            if self.stack_name == config_options["stack_name"]:
                if not self.region:
                    self.region = config_options.get("region", None)
                if not self.profile:
                    self.profile = config_options.get("profile", None)
                self.s3_bucket = config_options.get("s3_bucket", None)
                self.s3_prefix = config_options.get("s3_prefix", None)

    def delete(self):
        """
        Delete method calls for Cloudformation stacks and S3 and ECR artifacts
        """
        template = self.cf_utils.get_stack_template(self.stack_name, TEMPLATE_STAGE)
        template_str = template.get("TemplateBody", None)
        template_dict = yaml_parse(template_str)

        if self.s3_bucket and self.s3_prefix and template_str:
            self.delete_artifacts_folder = confirm(
                click.style(
                    "\tAre you sure you want to delete the folder"
                    + f" {self.s3_prefix} in S3 which contains the artifacts?",
                    bold=True,
                ),
                default=False,
            )
            if not self.delete_artifacts_folder:
                with mktempfile() as temp_file:
                    self.cf_template_file_name = get_cf_template_name(temp_file, template_str, "template")
                self.delete_cf_template_file = confirm(
                    click.style(
                        "\tDo you want to delete the template file" + f" {self.cf_template_file_name} in S3?", bold=True
                    ),
                    default=False,
                )

        # Delete the primary stack
        self.cf_utils.delete_stack(stack_name=self.stack_name)
        self.cf_utils.wait_for_delete(self.stack_name)
        
        click.echo(f"\n\t- Deleting Cloudformation stack {self.stack_name}")
        
        # Delete the artifacts
        template = Template(None, None, self.uploaders, None)
        template.delete(template_dict)
              
        # Delete the CF template file in S3
        if self.delete_cf_template_file:
            self.s3_uploader.delete_artifact(remote_path=self.cf_template_file_name)

        # Delete the folder of artifacts if s3_bucket and s3_prefix provided
        elif self.delete_artifacts_folder:
            self.s3_uploader.delete_prefix_artifacts()

    def run(self):
        """
        Delete the stack based on the argument provided by customers and samconfig.toml.
        """
        delete_stack = confirm(
            click.style(
                f"\tAre you sure you want to delete the stack {self.stack_name}" + f" in the region {self.region} ?",
                bold=True,
            ),
            default=False,
        )
        # Fetch the template using the stack-name
        if delete_stack and self.region:
            boto_config = get_boto_config_with_user_agent()

            # Define cf_client based on the region as different regions can have same stack-names
            cloudformation_client = boto3.client(
                "cloudformation", region_name=self.region if self.region else None, config=boto_config
            )

            s3_client = boto3.client("s3", region_name=self.region if self.region else None, config=boto_config)
            ecr_client = boto3.client("ecr", region_name=self.region if self.region else None, config=boto_config)

            self.s3_uploader = S3Uploader(s3_client=s3_client, bucket_name=self.s3_bucket, prefix=self.s3_prefix)

            docker_client = docker.from_env()
            ecr_uploader = ECRUploader(docker_client, ecr_client, None, None)
            
            self.uploaders = Uploaders(self.s3_uploader, ecr_uploader)
            self.cf_utils = CfUtils(cloudformation_client)

            is_deployed = self.cf_utils.has_stack(stack_name=self.stack_name)

            if is_deployed:
                self.delete()
                click.echo("\nDeleted successfully")
            else:
                click.echo(f"Error: The input stack {self.stack_name} does not exist on Cloudformation")
