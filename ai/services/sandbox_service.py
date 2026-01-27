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
        try:
            import contextlib
            import io
            import types

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
                    if name in ("os", "sys", "subprocess", "importlib", "builtins", "__import__", "__loader__"):
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
                exec(code, restricted_globals)

            result = output.getvalue()
            return result if result else "Code executed successfully (no output)"
        except Exception as e:
            return f"Code error: {e}"
