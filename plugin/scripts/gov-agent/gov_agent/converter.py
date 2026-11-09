"""첨부 변환 자리. 실제 변환은 Claude 세션이 한다(hwp·hwpx는 kordoc 스킬, 그 밖은 markitdown, D27).

외부 명령(예: kordoc)을 호출하는 인터페이스와, 실패하면 '읽지 못함'으로 남기는 처리만 둔다.
이 단계는 11/6 시험 전까지 확정하지 않았다(가정).
"""
import subprocess


def run_command(command, path):
    """command 의 {path} 를 파일 경로로 바꿔 실행하고 표준출력(텍스트)을 돌려준다. 실패하면 None."""
    try:
        r = subprocess.run([a.replace("{path}", str(path)) for a in command], capture_output=True,
                           text=True, encoding="utf-8", timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 and r.stdout.strip() else None


def convert_attachments(attachments, convert):
    """attachments: [{"name","url"}], convert(att) -> 텍스트 또는 None. (텍스트 목록, 읽지 못한 첨부 목록)."""
    texts, unreadable = [], []
    for att in attachments:
        try:
            text = convert(att)
        except Exception:
            text = None
        if text:
            texts.append(text)
        else:
            unreadable.append({"name": att.get("name"), "url": att.get("url")})
    return texts, unreadable
