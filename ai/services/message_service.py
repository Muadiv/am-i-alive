from __future__ import annotations


class MessageService:
    def __init__(self, observer_client) -> None:
        self.observer_client = observer_client

    async def check_votes(self) -> str:
        try:
            votes = await self.observer_client.fetch_votes()

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
            data = await self.observer_client.fetch_messages()
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

            await self.observer_client.mark_messages_read(message_ids)
            await report_activity("messages_read", f"Read {len(messages_list)} messages")
            return result
        except Exception as e:
            return f"Could not read messages: {e}"

    async def check_state(self) -> str:
        try:
            state = await self.observer_client.fetch_state()

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
