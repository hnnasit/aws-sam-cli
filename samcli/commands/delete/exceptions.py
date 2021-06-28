"""
Exceptions that are raised by sam delete
"""
from samcli.commands.exceptions import UserException


class DeleteFailedError(UserException):
    def __init__(self, stack_name, msg):
        self.stack_name = stack_name
        self.msg = msg

        message_fmt = "Failed to delete the stack: {stack_name}, {msg}"

        super().__init__(message=message_fmt.format(stack_name=self.stack_name, msg=msg))
