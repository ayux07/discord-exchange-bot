# utils/transcript.py
import html
import discord


async def build_transcript(channel: discord.TextChannel) -> bytes:
    rows = []
    async for m in channel.history(limit=None, oldest_first=True):
        ts = m.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        author = html.escape(f"{m.author} ({m.author.id})")
        body = html.escape(m.content or "").replace("\n", "<br>")

        extras = []
        for a in m.attachments:
            extras.append(f'<div class="att">📎 <a href="{html.escape(a.url)}">{html.escape(a.filename)}</a></div>')

        for e in m.embeds:
            parts = []
            if e.title:
                parts.append(f"<b>{html.escape(e.title)}</b>")
            if e.description:
                parts.append(html.escape(e.description).replace("\n", "<br>"))
            for f in e.fields:
                parts.append(f"<b>{html.escape(f.name)}:</b> {html.escape(f.value).replace(chr(10), '<br>')}")
            extras.append('<div class="embed">' + "<br>".join(parts) + "</div>")

        rows.append(
            f'<div class="msg"><div class="meta"><b>{author}</b> <span class="ts">{ts}</span></div>'
            f'<div>{body}</div>{"".join(extras)}</div>'
        )

    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Transcript - {html.escape(channel.name)}</title>
<style>
body {{ background:#313338; color:#dbdee1; font-family:Arial,sans-serif; padding:20px; }}
.msg {{ padding:8px 0; border-bottom:1px solid #3f4147; }}
.ts {{ color:#949ba4; font-size:12px; margin-left:8px; }}
.embed {{ border-left:4px solid #5865F2; background:#2b2d31; padding:8px; margin-top:4px; }}
.att a {{ color:#00a8fc; }}
</style></head><body>
<h2>#{html.escape(channel.name)}</h2><p>{len(rows)} messages</p>
{"".join(rows)}
</body></html>"""
    return page.encode("utf-8")
