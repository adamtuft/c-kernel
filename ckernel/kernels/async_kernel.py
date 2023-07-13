import asyncio
from typing import Literal

from .base_kernel import BaseKernel


class AsyncKernel(BaseKernel):

    async def do_execute(self, code: str, silent, store_history=True, user_expressions=None, allow_stdin=False, cell_id=None):
        response = await super().do_execute(code, silent, store_history=store_history, user_expressions=user_expressions, allow_stdin=allow_stdin, cell_id=cell_id)
        if response["status"] == "ok":
            commands = [line[3:].strip() for line in code.splitlines() if line.startswith("//%")]
            for command in commands:
                proc = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                streams = self.stream_data(proc.stdout, "stdout"), self.stream_data(proc.stderr, "stderr")
                await asyncio.gather(*streams, proc.wait())
                if proc.returncode != 0:
                    self.send_text("stderr", f"command failed with exit code {proc.returncode}:\n  $> {command}")
                    break
        return response

    async def stream_data(self, stream: asyncio.StreamReader, name: Literal["stderr", "stdout"]) -> None:
        async for data in stream:
            self.send_text(name, data.decode())
