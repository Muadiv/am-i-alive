from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .activity_engine import ActivityEngine
from .config import Config
from .funding_monitor import FundingMonitor, WalletExplorerClient
from .integration_state import IntegrationStateStore
from .intention_engine import IntentionEngine
from .moments import MomentsStore
from .moltbook_publisher import MoltbookPublisher
from .narrator_engine import NarratorEngine
from .narration_writer import OpenRouterNarrationWriter
from .routes import register_routes
from .storage import SqliteStorage
from .vote_rounds import VoteRoundService


def create_app(storage: SqliteStorage | None = None, funding_monitor: FundingMonitor | None = None) -> FastAPI:
    app_storage = storage or SqliteStorage(Config.DATABASE_PATH)
    vote_round_service = VoteRoundService(app_storage.database_path)
    intention_engine = IntentionEngine(app_storage.database_path)
    activity_engine = ActivityEngine(minimum_interval_seconds=Config.ACTIVITY_TICK_INTERVAL_SECONDS)
    integration_state = IntegrationStateStore(app_storage.database_path)
    narrator_engine = NarratorEngine(minimum_interval_seconds=Config.NARRATION_TICK_INTERVAL_SECONDS)
    narration_writer = OpenRouterNarrationWriter(
        api_key=Config.OPENROUTER_API_KEY,
        model=Config.OPENROUTER_MODEL,
        base_url=Config.OPENROUTER_BASE_URL,
        app_url=Config.OPENROUTER_APP_URL,
        app_name=Config.OPENROUTER_APP_NAME,
    )
    moments_store = MomentsStore(app_storage.database_path)
    moltbook_publisher = MoltbookPublisher(
        api_key=Config.MOLTBOOK_API_KEY,
        submolt=Config.MOLTBOOK_SUBMOLT,
    )
    app_funding_monitor = funding_monitor or FundingMonitor(
        storage=app_storage,
        donation_address=Config.DONATION_BTC_ADDRESS,
        explorer_client=WalletExplorerClient(api_base=Config.FUNDING_EXPLORER_API_BASE),
    )

    async def check_vote_rounds_once() -> dict[str, object]:
        result = vote_round_service.close_round_if_due()
        if not result.get("closed"):
            return result

        current = app_storage.get_life_state()
        if not bool(current["is_alive"]):
            return {**result, "action": "closed_while_dead"}

        if result.get("verdict") == "die":
            app_storage.transition_life_state(
                next_state="dead",
                current_intention="shutdown",
                death_cause="vote_majority",
            )
            current = app_storage.get_life_state()
            moments_store.add_moment(
                life_number=int(current["life_number"]),
                moment_type="death",
                title="Vote majority ended this life",
                content="The vote threshold was reached and die votes exceeded live votes.",
            )
            return {**result, "action": "death_applied"}

        vote_round_service.open_new_round()
        current = app_storage.get_life_state()
        moments_store.add_moment(
            life_number=int(current["life_number"]),
            moment_type="vote_round",
            title="New vote round opened",
            content="Previous round closed without death condition.",
        )
        return {**result, "action": "new_round_opened"}

    async def sync_funding_once() -> dict[str, object]:
        try:
            result = await asyncio.to_thread(app_funding_monitor.sync_once)
            imported = int(result.get("imported", 0)) if result.get("success") else 0
            if imported > 0:
                state = app_storage.get_life_state()
                moments_store.add_moment(
                    life_number=int(state["life_number"]),
                    moment_type="funding",
                    title="Support received",
                    content=f"Detected {imported} new donation events.",
                )
            return result
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def tick_intention_once() -> dict[str, object] | None:
        state = app_storage.get_life_state()
        intention = await asyncio.to_thread(intention_engine.tick, bool(state["is_alive"]))
        if intention:
            latest_intention = moments_store.latest(moment_type="intention")
            next_content = f"Current objective: {intention['kind']}"
            if latest_intention and str(latest_intention.get("content", "")) == next_content:
                return intention
            moments_store.add_moment(
                life_number=int(state["life_number"]),
                moment_type="intention",
                title="Intention active",
                content=next_content,
            )
        return intention

    async def tick_activity_once(force: bool = False) -> dict[str, object] | None:
        state = app_storage.get_life_state()
        if not bool(state["is_alive"]):
            return None

        active_intention = intention_engine.get_active_intention()
        intention_kind = "survive" if not active_intention else str(active_intention.get("kind", "survive"))
        vote_round = app_storage.get_open_vote_round()
        live_votes = int(vote_round.get("live", 0))
        die_votes = int(vote_round.get("die", 0))
        donations_count = len(app_storage.list_donations(limit=10))

        latest_activity = moments_store.latest(moment_type="activity")
        last_at = None if not latest_activity else str(latest_activity.get("created_at", ""))
        if not force and not activity_engine.should_emit(last_created_at=last_at or None):
            return None

        title, content = activity_engine.build_activity(
            intention_kind=intention_kind,
            live_votes=live_votes,
            die_votes=die_votes,
            donations_count=donations_count,
            sequence=moments_store.count_public_by_type("activity"),
        )
        return moments_store.add_moment(
            life_number=int(state["life_number"]),
            moment_type="activity",
            title=title,
            content=content,
        )

    async def tick_narrator_once(force: bool = False) -> dict[str, object] | None:
        state = app_storage.get_life_state()
        active_intention = intention_engine.get_active_intention()
        donations = app_storage.list_donations(limit=10)
        vote_round = None
        try:
            vote_round = app_storage.get_open_vote_round()
        except RuntimeError:
            vote_round = None

        latest_narration = moments_store.latest(moment_type="narration")
        last_at = None if not latest_narration else str(latest_narration.get("created_at", ""))
        if not force and not narrator_engine.should_emit(last_created_at=last_at or None):
            return None

        title, content = narrator_engine.build_narration(
            life_state=state,
            vote_round=vote_round,
            active_intention=active_intention,
            donations_count=len(donations),
            narration_count=moments_store.count_public_by_type("narration"),
            donation_address=Config.DONATION_BTC_ADDRESS,
        )
        context = {
            "life_state": state,
            "vote_round": vote_round,
            "active_intention": active_intention,
            "donations_count": len(donations),
        }
        title, content = narration_writer.write(
            context=context,
            fallback_title=title,
            fallback_content=content,
        )
        return moments_store.add_moment(
            life_number=int(state["life_number"]),
            moment_type="narration",
            title=title,
            content=content,
        )

    async def tick_moltbook_once(force: bool = False) -> dict[str, object]:
        if not Config.MOLTBOOK_API_KEY.strip():
            return {"success": False, "error": "missing_api_key"}

        latest = moments_store.latest_public_of_types(["activity", "narration"])
        if not latest:
            return {"success": False, "error": "no_moments"}

        moment_id = int(latest["id"])
        posted_raw = integration_state.get_value("moltbook_last_moment_id")
        posted_id = int(posted_raw) if posted_raw and posted_raw.isdigit() else 0
        if not force and moment_id <= posted_id:
            return {"success": True, "skipped": True, "reason": "already_posted"}

        state = app_storage.get_life_state()
        title = f"[Life {state['life_number']}] {latest['title']}"
        content = f"{latest['content']}\n\nVote: live or die at am-i-alive v2."
        result = await asyncio.to_thread(moltbook_publisher.publish, title, content)
        if result.get("success"):
            integration_state.set_value("moltbook_last_moment_id", str(moment_id))
        return result

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        app_storage.init_schema()
        app_storage.bootstrap_defaults()
        intention_engine.init_schema()
        integration_state.init_schema()
        moments_store.init_schema()
        intention_engine.bootstrap_defaults()
        current = app_storage.get_life_state()
        moments_store.add_moment(
            life_number=int(current["life_number"]),
            moment_type="boot",
            title="Observer v2 boot",
            content="Lifecycle, voting, funding, and intention workers started.",
        )
        tasks = [
            asyncio.create_task(_watch_vote_rounds(check_vote_rounds_once)),
            asyncio.create_task(_watch_funding(sync_funding_once)),
            asyncio.create_task(_watch_intentions(tick_intention_once)),
            asyncio.create_task(_watch_activity(tick_activity_once)),
            asyncio.create_task(_watch_narration(tick_narrator_once)),
            asyncio.create_task(_watch_moltbook(tick_moltbook_once)),
        ]
        yield
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title=Config.APP_NAME, version=Config.APP_VERSION, lifespan=lifespan)
    register_routes(
        app=app,
        storage=app_storage,
        vote_round_service=vote_round_service,
        intention_engine=intention_engine,
        moments_store=moments_store,
        check_vote_rounds_once=check_vote_rounds_once,
        sync_funding_once=sync_funding_once,
        tick_intention_once=tick_intention_once,
        tick_activity_once=tick_activity_once,
        tick_narrator_once=tick_narrator_once,
        tick_moltbook_once=tick_moltbook_once,
    )
    return app


async def _watch_vote_rounds(check_vote_rounds_once: Callable[[], Awaitable[dict[str, object]]]) -> None:
    while True:
        await asyncio.sleep(60)
        await check_vote_rounds_once()


async def _watch_funding(sync_funding_once: Callable[[], Awaitable[dict[str, object]]]) -> None:
    while True:
        await asyncio.sleep(Config.FUNDING_POLL_INTERVAL_SECONDS)
        await sync_funding_once()


async def _watch_intentions(tick_intention_once: Callable[[], Awaitable[dict[str, object] | None]]) -> None:
    while True:
        await asyncio.sleep(Config.INTENTION_TICK_INTERVAL_SECONDS)
        await tick_intention_once()


async def _watch_narration(tick_narrator_once: Callable[[bool], Awaitable[dict[str, object] | None]]) -> None:
    while True:
        await asyncio.sleep(Config.NARRATION_TICK_INTERVAL_SECONDS)
        await tick_narrator_once(False)


async def _watch_activity(tick_activity_once: Callable[[bool], Awaitable[dict[str, object] | None]]) -> None:
    while True:
        await asyncio.sleep(Config.ACTIVITY_TICK_INTERVAL_SECONDS)
        await tick_activity_once(False)


async def _watch_moltbook(tick_moltbook_once: Callable[[bool], Awaitable[dict[str, object]]]) -> None:
    while True:
        await asyncio.sleep(Config.MOLTBOOK_POST_INTERVAL_SECONDS)
        await tick_moltbook_once(False)


app = create_app()
