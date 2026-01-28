from typing import Protocol

from .services.action_params import get_int_param, get_str_list_param, get_str_param


class BrainInterface(Protocol):
    async def report_activity(self, action: str, details: str | None = None) -> None: ...

    async def report_thought(self, content: str, thought_type: str = "thought") -> None: ...

    async def ask_echo(self, question: str) -> str: ...

    async def post_to_telegram(self, content: str) -> str: ...

    async def write_blog_post(self, title: str, content: str, tags: list[str]) -> str: ...

    async def check_votes(self) -> str: ...

    async def check_system(self) -> str: ...

    async def check_system_stats(self) -> str: ...

    async def check_health(self) -> str: ...

    async def check_processes(self) -> str: ...

    async def check_disk_cleanup(self) -> str: ...

    async def check_services(self) -> str: ...

    async def check_logs(self, service: str, lines: int = 50) -> str: ...

    async def check_state_internal(self) -> str: ...

    async def check_budget(self) -> str: ...

    def check_twitter_status_action(self) -> str: ...

    async def read_messages(self) -> str: ...

    async def switch_model(self, model_id: str) -> str: ...

    async def list_available_models(self) -> str: ...

    async def check_model_health(self) -> str: ...

    def read_file(self, path: str) -> str: ...

    def write_file(self, path: str, content: str) -> str: ...

    def run_code(self, code: str) -> str: ...

    def adjust_think_interval(self, duration: int) -> str: ...

    async def control_led(self, state: str) -> str: ...


class ActionExecutor:
    def __init__(self, brain: BrainInterface) -> None:
        self.brain = brain

    async def execute_action(self, action: str, params: dict[str, object]) -> str:
        if action == "ask_echo":
            question = get_str_param(params, "question")
            return await self.brain.ask_echo(question)

        if action == "post_x":
            return "❌ X/Twitter posting is currently disabled. Use post_telegram to reach the outside world!"

        if action == "post_telegram":
            return (
                "❌ Direct Telegram posts are disabled. Publish via write_blog_post so the channel stays focused "
                "on blog updates."
            )

        if action == "write_blog_post":
            title = get_str_param(params, "title")
            content = get_str_param(params, "content")
            tags = get_str_list_param(params, "tags")
            return await self.brain.write_blog_post(title, content, tags)

        if action == "check_votes":
            return await self.brain.check_votes()

        if action == "check_system":
            return await self.brain.check_system()

        if action == "check_system_stats":
            return await self.brain.check_system_stats()

        if action == "check_health":
            return await self.brain.check_health()

        if action == "check_processes":
            return await self.brain.check_processes()

        if action == "check_disk_cleanup":
            return await self.brain.check_disk_cleanup()

        if action == "check_services":
            return await self.brain.check_services()

        if action == "check_logs":
            service = get_str_param(params, "service")
            lines = get_int_param(params, "lines", default=50)
            return await self.brain.check_logs(service, lines)

        if action == "check_state":
            return await self.brain.check_state_internal()

        if action == "check_budget":
            return await self.brain.check_budget()

        if action == "check_twitter_status":
            return self.brain.check_twitter_status_action()

        if action == "read_messages":
            return await self.brain.read_messages()

        if action == "switch_model":
            model_id = get_str_param(params, "model_id")
            return await self.brain.switch_model(model_id)

        if action == "list_models":
            return await self.brain.list_available_models()

        if action == "check_model_health":
            return await self.brain.check_model_health()

        if action == "read_file":
            path = get_str_param(params, "path")
            return self.brain.read_file(path)

        if action == "write_file":
            path = get_str_param(params, "path")
            content = get_str_param(params, "content")
            return self.brain.write_file(path, content)

        if action == "run_code":
            code = get_str_param(params, "code")
            return self.brain.run_code(code)

        if action == "sleep":
            duration = get_int_param(params, "duration", default=10)
            return self.brain.adjust_think_interval(duration)

        if action == "reflect":
            return "Reflection complete. Inner thoughts processed."

        if action == "control_led":
            state = get_str_param(params, "state")
            return await self.brain.control_led(state)

        return f"Unknown action: {action}"
