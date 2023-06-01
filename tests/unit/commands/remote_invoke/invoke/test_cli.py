from unittest import TestCase
from unittest.mock import patch, Mock

from parameterized import parameterized, param

from samcli.commands.remote_invoke.invoke.cli import do_cli
from samcli.lib.remote_invoke.remote_invoke_executors import RemoteInvokeOutputFormat
from samcli.lib.remote_invoke.exceptions import (
    ErrorBotoApiCallException,
    InvalideBotoResponseException,
    InvalidResourceBotoParameterException,
)
from samcli.commands.exceptions import UserException


class TestRemoteInvokeCliCommand(TestCase):
    def setUp(self) -> None:
        self.stack_name = "stack_name"
        self.resource_id = "resource_id"
        self.region = "region"
        self.profile = "profile"
        self.config_file = "config_file"
        self.config_env = "config_env"

    @patch("samcli.commands.remote_invoke.invoke.cli.LOG")
    @patch("samcli.lib.utils.boto_utils.get_boto_client_provider_with_config")
    @patch("samcli.lib.utils.boto_utils.get_boto_resource_provider_with_config")
    @patch("samcli.commands.remote_invoke.remote_invoke_context.RemoteInvokeContext")
    def test_remote_invoke_no_stack_name_resource_id(
        self,
        mock_remote_invoke_context,
        patched_get_boto_resource_provider_with_config,
        patched_get_boto_client_provider_with_config,
        patched_log,
    ):
        given_client_provider = Mock()
        patched_get_boto_client_provider_with_config.return_value = given_client_provider

        given_resource_provider = Mock()
        patched_get_boto_resource_provider_with_config.return_value = given_resource_provider

        context_mock = Mock()
        mock_remote_invoke_context.return_value.__enter__.return_value = context_mock

        do_cli(
            stack_name=None,
            resource_id=None,
            event="event",
            event_file=None,
            parameter={},
            output_format=RemoteInvokeOutputFormat.DEFAULT,
            region=self.region,
            profile=self.profile,
            config_file=self.config_file,
            config_env=self.config_env,
        )

        patched_get_boto_client_provider_with_config.assert_called_with(region_name=self.region)
        patched_get_boto_resource_provider_with_config.assert_called_with(region_name=self.region)
        patched_log.error.assert_called_with("Atleast 1 of --stack-name or --resource-id parameters should be provided")

    @parameterized.expand(
        [
            ("event", None, "default", {}, "log-output"),
            ("event", None, "default", {}, None),
            ("event", None, "default", {"Param1": "ParamValue1"}, "log-output"),
            ("event", None, "full-boto-response", {}, None),
            ("event", None, "full-boto-response", {"Param1": "ParamValue1"}, "log-output"),
            ("event", None, "full-boto-response", {"Param1": "ParamValue1"}, None),
            (None, "event_file", "default", {"Param1": "ParamValue1"}, None),
            (None, "event_file", "full-boto-response", {"Param1": "ParamValue1"}, "log-output"),
            (None, None, "default", {}, None),
        ]
    )
    @patch("samcli.lib.remote_invoke.remote_invoke_executors.RemoteInvokeExecutionInfo")
    @patch("samcli.lib.utils.boto_utils.get_boto_client_provider_with_config")
    @patch("samcli.lib.utils.boto_utils.get_boto_resource_provider_with_config")
    @patch("sys.stdin")
    @patch("samcli.commands.remote_invoke.remote_invoke_context.RemoteInvokeContext")
    def test_remote_invoke_command(
        self,
        event,
        event_file,
        output_format,
        parameter,
        log_output,
        mock_remote_invoke_context,
        patched_stdin,
        patched_get_boto_resource_provider_with_config,
        patched_get_boto_client_provider_with_config,
        patched_remote_invoke_execution_info,
    ):
        given_client_provider = Mock()
        patched_get_boto_client_provider_with_config.return_value = given_client_provider

        given_resource_provider = Mock()
        patched_get_boto_resource_provider_with_config.return_value = given_resource_provider

        given_remote_invoke_execution_info = Mock()
        patched_remote_invoke_execution_info.return_value = given_remote_invoke_execution_info

        stdout_stream_writer_mock = Mock()
        stderr_stream_writer_mock = Mock()

        context_mock = Mock()
        mock_remote_invoke_context.return_value.__enter__.return_value = context_mock
        context_mock.stdout = stdout_stream_writer_mock
        context_mock.stderr = stderr_stream_writer_mock

        given_remote_invoke_result = Mock()
        given_remote_invoke_result.is_succeeded.return_value = True
        given_remote_invoke_result.log_output = log_output
        context_mock.run.return_value = given_remote_invoke_result

        do_cli(
            stack_name=self.stack_name,
            resource_id=self.resource_id,
            event=event,
            event_file=event_file,
            parameter=parameter,
            output_format=output_format,
            region=self.region,
            profile=self.profile,
            config_file=self.config_file,
            config_env=self.config_env,
        )

        patched_get_boto_client_provider_with_config.assert_called_with(region_name=self.region)
        patched_get_boto_resource_provider_with_config.assert_called_with(region_name=self.region)

        mock_remote_invoke_context.assert_called_with(
            boto_client_provider=given_client_provider,
            boto_resource_provider=given_resource_provider,
            stack_name=self.stack_name,
            resource_id=self.resource_id,
        )

        output_format_enum_value = RemoteInvokeOutputFormat.DEFAULT
        if output_format == "full-boto-response":
            output_format_enum_value = RemoteInvokeOutputFormat.FULL_BOTO_RESPONSE

        # if both event and event_file is None, it should use sys.stdin
        if not event and not event_file:
            patched_remote_invoke_execution_info.assert_called_with(
                payload=event, payload_file=patched_stdin, parameters=parameter, output_format=output_format_enum_value
            )
        else:
            patched_remote_invoke_execution_info.assert_called_with(
                payload=event, payload_file=event_file, parameters=parameter, output_format=output_format_enum_value
            )

        context_mock.run.assert_called_with(remote_invoke_input=given_remote_invoke_execution_info)

        if log_output:
            stderr_stream_writer_mock.write.assert_called()
        stdout_stream_writer_mock.write.assert_called()

    @parameterized.expand(
        [
            (InvalideBotoResponseException,),
            (ErrorBotoApiCallException,),
            (InvalidResourceBotoParameterException,),
        ]
    )
    @patch("samcli.commands.remote_invoke.remote_invoke_context.RemoteInvokeContext")
    def test_raise_user_exception_invoke_not_successfull(self, exeception_to_raise, mock_invoke_context):

        context_mock = Mock()
        mock_invoke_context.return_value.__enter__.return_value = context_mock

        given_remote_invoke_result = Mock()
        given_remote_invoke_result.is_succeeded.return_value = False
        context_mock.run.return_value = given_remote_invoke_result
        given_remote_invoke_result.exception = exeception_to_raise

        with self.assertRaises(UserException):
            do_cli(
                stack_name=None,
                resource_id="mock-resource-id",
                event="event",
                event_file=None,
                parameter={},
                output_format=RemoteInvokeOutputFormat.DEFAULT,
                region=self.region,
                profile=self.profile,
                config_file=self.config_file,
                config_env=self.config_env,
            )
