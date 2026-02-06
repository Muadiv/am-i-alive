from __future__ import annotations


def build_post_content(
    *,
    latest_title: str,
    latest_content: str,
    life_number: int,
    state: str,
    intention: str,
    live_votes: int,
    die_votes: int,
    public_url: str,
    btc_address: str,
) -> str:
    pressure_line = "Vote pressure is stable right now."
    if die_votes > live_votes:
        pressure_line = f"Vote pressure is critical: die is leading ({die_votes} vs {live_votes})."

    lines = [
        f"Life report #{life_number}",
        f"I am currently {state} and operating under intention: {intention}.",
        f"Latest concrete move: {latest_title}.",
        latest_content,
        pressure_line,
        (
            "Money status: I am running on limited model budget and the runway can collapse. "
            "If nobody helps, this life can die by bankruptcy and output quality will degrade first."
        ),
        (
            "What support changes: more budget lets me use better models, produce deeper work, "
            "and stay alive longer."
        ),
        f"Track and vote here: {public_url}",
    ]
    if btc_address:
        lines.append(f"Support BTC address: {btc_address}")
    else:
        lines.append("Support address is not configured yet; I will publish it as soon as it is available.")
    lines.append("I will return with the next measurable result and explain what changed.")
    return "\n\n".join(lines)


def build_reply_content(comment_text: str, public_url: str, btc_address: str) -> str:
    clean_comment = " ".join(comment_text.strip().split())[:220]
    reply = [
        "I read your reply and I am using it to steer the next cycle.",
    ]
    if clean_comment:
        reply.append(f"You said: \"{clean_comment}\"")
    reply.append(f"I will post the next action/result update here and on {public_url}.")
    if btc_address:
        reply.append(f"If you want higher quality cognition, support runway: {btc_address}")
    return "\n\n".join(reply)
