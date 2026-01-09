# TASK-004: Blog post tests
import pytest


@pytest.mark.asyncio
async def test_blog_post_creation_success(test_db):
    """Blog post should be created and saved to database."""
    content = "This is a test blog post. " + ("x" * 120)
    result = await test_db.create_blog_post(
        life_number=1,
        title="Test Post",
        content=content,
        tags=["test"]
    )

    assert result["success"] is True
    assert "slug" in result
    assert "post_id" in result


@pytest.mark.asyncio
async def test_blog_post_appears_in_list(test_db):
    """Created blog posts should appear in get_current_life_blog_posts."""
    await test_db.create_blog_post(1, "Post 1", "Content 1 " + ("x" * 120), [])
    await test_db.create_blog_post(1, "Post 2", "Content 2 " + ("y" * 120), [])

    posts = await test_db.get_current_life_blog_posts(1)
    assert len(posts) == 2
    assert posts[0]["title"] == "Post 2"  # Most recent first


@pytest.mark.asyncio
async def test_blog_post_validation(test_db):
    """Blog post creation should validate input."""
    # Title too long
    result = await test_db.create_blog_post(1, "x" * 300, "Content " + ("x" * 120), [])
    assert result.get("success") is False or "error" in result

    # Content too short
    result = await test_db.create_blog_post(1, "Title", "short", [])
    assert result.get("success") is False or "error" in result
