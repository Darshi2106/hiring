"""Email service — Resend if configured, otherwise logs to console (no-op stub)."""
import os
import asyncio
import logging

logger = logging.getLogger("email")


def build_invite_email_html(candidate_name: str, job_title: str, exam_url: str, duration: int) -> str:
    return f"""
    <html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#f4f4f5;padding:24px;color:#09090b;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e4e4e7;">
        <tr>
          <td style="padding:24px 32px;border-bottom:1px solid #e4e4e7;">
            <div style="font-weight:800;font-size:20px;color:#103e43;letter-spacing:-0.02em;">CohortData Hiring</div>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <h2 style="margin:0 0 8px 0;font-size:24px;color:#103e43;letter-spacing:-0.02em;">Hi {candidate_name},</h2>
            <p style="margin:0 0 16px 0;font-size:15px;line-height:1.6;color:#3f3f46;">
              Thank you for applying to <strong>{job_title}</strong>. As the next step, please complete the following proctored assessment.
            </p>
            <table cellpadding="0" cellspacing="0" style="margin:16px 0;">
              <tr>
                <td style="padding:6px 12px;background:#fafafa;border-left:3px solid #0f9394;font-size:13px;color:#3f3f46;">
                  Duration: <strong>{duration} minutes</strong> · One-time link · Webcam & fullscreen required
                </td>
              </tr>
            </table>
            <p style="margin:16px 0;font-size:14px;color:#3f3f46;">
              Before starting: ensure you have a working webcam, a quiet space, and a stable internet connection. Once started the assessment must be completed in one sitting.
            </p>
            <table cellpadding="0" cellspacing="0" style="margin:24px 0;">
              <tr><td>
                <a href="{exam_url}" style="display:inline-block;background:#0f9394;color:#ffffff;text-decoration:none;padding:14px 28px;font-weight:600;font-size:15px;">Start assessment →</a>
              </td></tr>
            </table>
            <p style="margin:16px 0 0 0;font-size:12px;color:#71717a;">
              If the button doesn't work, copy this link into your browser:<br/>
              <span style="font-family:monospace;color:#0f9394;word-break:break-all;">{exam_url}</span>
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:16px 32px;background:#fafafa;border-top:1px solid #e4e4e7;font-size:12px;color:#71717a;">
            This link is unique to you and expires after submission. Do not share it.
          </td>
        </tr>
      </table>
    </body></html>
    """


async def send_invite_email(
    to_email: str,
    candidate_name: str,
    job_title: str,
    exam_url: str,
    duration: int,
    cc_master: bool = True,
) -> dict:
    """Send invite email via Resend if key configured; else log + return mocked."""
    subject = f"CohortData assessment — {job_title}"
    html = build_invite_email_html(candidate_name, job_title, exam_url, duration)
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
    master = os.environ.get("MASTER_ADMIN_EMAIL")
    key = os.environ.get("RESEND_API_KEY", "").strip()

    if not key:
        logger.warning(
            "[EMAIL:MOCK] to=%s subject=%s cc_master=%s exam_url=%s (no RESEND_API_KEY set)",
            to_email, subject, cc_master, exam_url,
        )
        return {"delivered": False, "mocked": True, "reason": "RESEND_API_KEY not configured"}

    try:
        import resend
        resend.api_key = key
        params = {
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": html,
        }
        if cc_master and master:
            params["cc"] = [master]
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info("[EMAIL:SENT] id=%s to=%s", result.get("id"), to_email)
        return {"delivered": True, "email_id": result.get("id")}
    except Exception as e:
        logger.error("[EMAIL:ERROR] %s", e)
        return {"delivered": False, "error": str(e)[:200]}
