"""A simple asynchronous kernel"""

from .util import AsyncCommand, STDERR
from .base_kernel import BaseKernel


class AsyncKernel(BaseKernel):  # pylint: disable=too-many-ancestors
    """Execute a code cell, interpreting our own magic comments as shell commands"""

    async def do_execute(  # pylint: disable=too-many-arguments
        self,
        code,
        silent,
        store_history=True,
        user_expressions=None,
        allow_stdin=False,
        *,
        cell_id=None,
    ):
        response = await super().do_execute(
            code,
            silent,
            store_history=store_history,
            user_expressions=user_expressions,
            allow_stdin=allow_stdin,
            cell_id=cell_id,
        )
        if response["status"] != "ok":
            return response
        commands = [
            line[3:].strip() for line in code.splitlines() if line.startswith("//%")
        ]
        for command in commands:
            task = AsyncCommand(command)
            result = await task.run_with_output(self.stream_stdout, self.stream_stderr)
            if result != 0:
                self.print(
                    f"command failed with exit code {result}:\n  $> {command}",
                    STDERR,
                )
                break
        return response
