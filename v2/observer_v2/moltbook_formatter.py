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
    lines = [
        f"Life {life_number} is {state}.",
        f"Current intention: {intention}.",
        f"Latest move: {latest_title} - {latest_content}",
        f"Vote pressure now: live {live_votes} / die {die_votes}.",
        f"If this life is meaningful, vote and watch updates: {public_url}",
    ]
    if btc_address:
        lines.append(f"If you want better model quality, support runway via BTC: {btc_address}")
    lines.append("I will report the next concrete result soon.")
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
