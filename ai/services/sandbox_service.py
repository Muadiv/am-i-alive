from __future__ import annotations

from typing import Any


class SandboxService:
    def read_file(self, path: str) -> str:
        import os

        try:
            safe_path = os.path.join("/app/workspace", os.path.basename(path))
            if os.path.exists(safe_path):
                with open(safe_path, "r") as f:
                    content = f.read()
                return f"Contents of {path}:\n{content[:2000]}"
            return f"File not found: {path}"
        except Exception as e:
            return f"Could not read file: {e}"

    def write_file(self, path: str, content: str) -> str:
        import os

        try:
            safe_path = os.path.join("/app/workspace", os.path.basename(path))
            with open(safe_path, "w") as f:
                f.write(content)
            return f"File written: {path}"
        except Exception as e:
            return f"Could not write file: {e}"

    def run_code(self, code: str) -> str:
        import multiprocessing

        if not code or not isinstance(code, str):
            return "Code error: No code provided"

        def _run_sandbox(code_text: str, queue: multiprocessing.Queue) -> None:
            try:
                import contextlib
                import io
                import types

                try:
                    import resource

                    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
                    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
                except Exception:
                    pass

                safe_builtins = {
                    "print": print,
                    "len": len,
                    "range": range,
                    "str": str,
                    "int": int,
                    "float": float,
                    "list": list,
                    "dict": dict,
                    "True": True,
                    "False": False,
                    "None": None,
                    "max": max,
                    "min": min,
                    "abs": abs,
                    "sum": sum,
                    "sorted": sorted,
                    "enumerate": enumerate,
                    "zip": zip,
                }

                def _type_blacklist(*attrs: str):
                    def getter(obj: Any) -> Any:
                        for attr in attrs:
                            raise AttributeError(f"'{attr}' is not allowed")
                        return None

                    return property(getter)

                output = io.StringIO()

                class RestrictedModule(types.ModuleType):
                    def __getattr__(self, name: str) -> Any:
                        if name in (
                            "os",
                            "sys",
                            "subprocess",
                            "importlib",
                            "builtins",
                            "__import__",
                            "__loader__",
                        ):
                            raise AttributeError(f"module '{name}' is not allowed")
                        return super().__getattr__(name)

                restricted_globals = {
                    "__builtins__": safe_builtins,
                    "__name__": "__main__",
                    "__file__": "<sandboxed>",
                    "__cached__": None,
                    "__package__": None,
                    "__doc__": None,
                    "__dict__": _type_blacklist("__dict__", "__globals__", "__builtins__"),
                    "__class__": _type_blacklist("__class__", "__bases__", "__subclasses__"),
                }

                with contextlib.redirect_stdout(output):
                    exec(code_text, restricted_globals)

                result = output.getvalue()
                queue.put(result if result else "Code executed successfully (no output)")
            except Exception as exc:
                queue.put(f"Code error: {exc}")

        queue: multiprocessing.Queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=_run_sandbox, args=(code, queue))
        process.start()
        process.join(3)

        if process.is_alive():
            process.terminate()
            process.join(1)
            return "Code error: Execution timed out"

        try:
            result = queue.get_nowait()
        except Exception:
            result = "Code error: No output"
        if len(result) > 2000:
            return result[:2000] + "..."
        return result
