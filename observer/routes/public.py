import bleach
import httpx
import markdown2
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

try:
    from database import get_all_blog_posts as get_all_blog_posts_db
    from database import get_blog_post_by_slug as get_blog_post_by_slug_db
    from database import get_blog_post_neighbors as get_blog_post_neighbors_db
    from database import get_current_life_blog_posts as get_current_life_blog_posts_db
    from database import get_current_state as get_current_state_db
    from database import get_death_count as get_death_count_db
    from database import get_life_history as get_life_history_db
    from database import get_recent_blog_posts as get_recent_blog_posts_db
    from database import get_recent_thoughts as get_recent_thoughts_db
    from database import get_site_stats as get_site_stats_db
    from database import get_unread_message_count as get_unread_message_count_db
    from database import get_vote_counts as get_vote_counts_db
    from database import track_visitor as track_visitor_db
except ImportError:
    from ..database import get_all_blog_posts as get_all_blog_posts_db
    from ..database import get_blog_post_by_slug as get_blog_post_by_slug_db
    from ..database import get_blog_post_neighbors as get_blog_post_neighbors_db
    from ..database import get_current_life_blog_posts as get_current_life_blog_posts_db
    from ..database import get_current_state as get_current_state_db
    from ..database import get_death_count as get_death_count_db
    from ..database import get_life_history as get_life_history_db
    from ..database import get_recent_blog_posts as get_recent_blog_posts_db
    from ..database import get_recent_thoughts as get_recent_thoughts_db
    from ..database import get_site_stats as get_site_stats_db
    from ..database import get_unread_message_count as get_unread_message_count_db
    from ..database import get_vote_counts as get_vote_counts_db
    from ..database import track_visitor as track_visitor_db

router = APIRouter()


def _get_context():
    try:
        import main as main_module
    except ImportError:
        from .. import main as main_module

    return (
        main_module.AI_API_URL,
        main_module.ALLOWED_ATTRIBUTES,
        main_module.ALLOWED_TAGS,
        main_module.get_client_ip,
        main_module.hash_ip,
        main_module.templates,
    )


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page - see the AI, vote, watch it live."""
    _, _, _, get_client_ip, hash_ip, templates = _get_context()
    client_ip = get_client_ip(request) or "unknown"
    ip_hash = hash_ip(client_ip)[:16]
    await track_visitor_db(ip_hash)

    state = await get_current_state_db()
    votes = await get_vote_counts_db()
    thoughts = await get_recent_thoughts_db(10)
    death_count = await get_death_count_db()
    message_count = await get_unread_message_count_db()
    site_stats = await get_site_stats_db()

    recent_posts = await get_recent_blog_posts_db(5)
    latest_post = recent_posts[0] if recent_posts else None

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "state": state,
            "votes": votes,
            "thoughts": thoughts,
            "recent_posts": recent_posts,
            "latest_post": latest_post,
            "death_count": death_count,
            "message_count": message_count,
            "site_stats": site_stats,
            "is_alive": state.get("is_alive", False),
        },
    )


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    """View past lives."""
    _, _, _, _, _, templates = _get_context()
    lives = await get_life_history_db()
    death_count = await get_death_count_db()
    return templates.TemplateResponse("history.html", {"request": request, "lives": lives, "death_count": death_count})


@router.get("/budget", response_class=HTMLResponse)
async def budget_page(request: Request):
    """View AI's budget and spending."""
    AI_API_URL, _, _, _, _, templates = _get_context()
    budget_data = {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AI_API_URL}/budget", timeout=5.0)
            budget_data = response.json()
            budget_data.setdefault("models", [])
            budget_data.setdefault(
                "totals", {"total_input_tokens": 0, "total_output_tokens": 0, "total_tokens": 0, "total_cost": 0.0}
            )
            budget_data.setdefault(
                "current_life",
                {
                    "life_number": budget_data.get("lives", 0),
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                },
            )
            budget_data.setdefault(
                "all_time",
                {
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "total_lives": budget_data.get("lives", 0),
                },
            )
    except Exception as e:
        print(f"[BUDGET] ⚠️ Failed to fetch budget data: {e}")
        budget_data = {"error": "Could not fetch budget data"}

    return templates.TemplateResponse("budget.html", {"request": request, "budget": budget_data})


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About page explaining the experiment."""
    _, _, _, _, _, templates = _get_context()
    return templates.TemplateResponse("about.html", {"request": request})


@router.get("/blog", response_class=HTMLResponse)
async def blog_page(request: Request):
    """Blog homepage - current life's posts only."""
    _, _, _, _, _, templates = _get_context()
    state = await get_current_state_db()
    posts = await get_current_life_blog_posts_db(state["life_number"], limit=20)

    memories = []
    if state["life_number"] > 1:
        try:
            memory_data = await get_life_history_db()
            if memory_data:
                previous_life = [life for life in memory_data if life["life_number"] == state["life_number"] - 1]
                if previous_life and previous_life[0].get("summary"):
                    summary = previous_life[0]["summary"]
                    memories = [s.strip() for s in summary.split(";") if s.strip()]
        except Exception:
            memories = []

    return templates.TemplateResponse(
        "blog.html", {"request": request, "posts": posts, "state": state, "memories": memories, "is_current_life": True}
    )


@router.get("/blog/history", response_class=HTMLResponse)
async def blog_history(request: Request):
    """Archive of ALL blog posts from all lives."""
    _, _, _, _, _, templates = _get_context()
    all_posts = await get_all_blog_posts_db(limit=100)

    posts_by_life = {}
    for post in all_posts:
        life = post["life_number"]
        if life not in posts_by_life:
            posts_by_life[life] = []
        posts_by_life[life].append(post)

    return templates.TemplateResponse(
        "blog_history.html", {"request": request, "posts_by_life": posts_by_life, "total_posts": len(all_posts)}
    )


@router.get("/chronicle", response_class=HTMLResponse)
async def chronicle(request: Request):
    """Public Chronicle page showing notable events timeline."""
    _, _, _, _, _, templates = _get_context()
    return templates.TemplateResponse("chronicle.html", {"request": request})


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str):
    """Individual blog post page."""
    _, ALLOWED_ATTRIBUTES, ALLOWED_TAGS, _, _, templates = _get_context()
    post = await get_blog_post_by_slug_db(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    neighbors = await get_blog_post_neighbors_db(slug)

    post["html_content"] = markdown2.markdown(post["content"], extras=["fenced-code-blocks", "tables", "header-ids"])
    post["html_content"] = bleach.clean(
        post["html_content"], tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True
    )

    return templates.TemplateResponse("blog_post.html", {"request": request, "post": post, "neighbors": neighbors})
