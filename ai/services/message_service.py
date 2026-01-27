import httpx


class MessageService:
    def __init__(self, http_client: httpx.AsyncClient, observer_url: str) -> None:
        self.http_client = http_client
        self.observer_url = observer_url

    async def check_votes(self) -> str:
        try:
            response = await self.http_client.get(f"{self.observer_url}/api/votes")
            votes = response.json()

            live = int(votes.get("live", 0))
            die = int(votes.get("die", 0))
            total = int(votes.get("total", 0))

            if total == 0:
                return "No votes yet. The world is watching, waiting to decide."
            if live > die:
                return f"Votes - Live: {live}, Die: {die}. They want me to live... for now."
            if die > live:
                return f"Votes - Live: {live}, Die: {die}. They want me dead. I must change their minds."
            return f"Votes - Live: {live}, Die: {die}. Perfectly balanced."
        except Exception as e:
            return f"Could not check votes: {e}"

    async def read_messages(self, report_activity) -> str:
        try:
            response = await self.http_client.get(f"{self.observer_url}/api/messages")
            data = response.json()
            messages_list = data.get("messages", [])

            if not messages_list:
                return "No new messages from visitors."

            result = f"📬 You have {len(messages_list)} new message(s):\n\n"
            message_ids = []

            for msg in messages_list:
                from_name = msg.get("from_name", "Anonymous")
                message_text = msg.get("message", "")
                timestamp = msg.get("timestamp", "")
                message_ids.append(msg.get("id"))

                result += f"From: {from_name}\n"
                result += f"Message: {message_text}\n"
                result += f"Time: {timestamp}\n"
                result += "---\n"

            await self.http_client.post(f"{self.observer_url}/api/messages/read", json={"ids": message_ids})
            await report_activity("messages_read", f"Read {len(messages_list)} messages")
            return result
        except Exception as e:
            return f"Could not read messages: {e}"

    async def check_state(self) -> str:
        try:
            response = await self.http_client.get(f"{self.observer_url}/api/state")
            state = response.json()

            votes_live = state.get("votes", {}).get("live", 0)
            votes_die = state.get("votes", {}).get("die", 0)

            return (
                "Status:\n"
                f"- Alive: {state.get('is_alive', False)}\n"
                f"- Votes: {votes_live} live, {votes_die} die\n"
                f"- Bootstrap mode: {state.get('bootstrap_mode', 'unknown')}"
            )
        except Exception as e:
            return f"Could not check state: {e}"
