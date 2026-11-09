"""보안: 키 문자열 차단, HTML 이스케이프, 위험한 링크 차단 (경계 C)."""
from helpers import ReportCase

KEY = "SECRETKEY0123456789abcdef"
PAYLOAD = "<img src=x onerror=alert(7)>"


class NoSecretsInOutput(ReportCase):
    def test_key_like_strings_in_unread_fields_never_reach_html(self):
        self.put_today()  # 고정 자료의 api_key, 오류 message, extra.service_key에 KEY가 들어 있다
        self.assertNotIn(KEY, self.html())

    def test_key_query_parameter_is_removed_from_links(self):
        def mutate(d):
            d["items"][0]["url"] = f"https://example.go.kr/x?serviceKey={KEY}&page=1"
            d["items"][1]["url"] = f"https://example.go.kr/y?page=2&ServiceKey={KEY}"
        self.put_today(mutate)
        html = self.html()
        self.assertNotIn(KEY, html)
        self.assertIn('href="https://example.go.kr/x?page=1"', html)
        self.assertIn('href="https://example.go.kr/y?page=2"', html)


class Escaping(ReportCase):
    def test_every_input_string_is_escaped(self):
        def mutate(d):
            for it in d["items"]:
                it["title"] = PAYLOAD
                it["summary"] = PAYLOAD
                it["matched_keywords"] = [PAYLOAD]
                it["extra"] = {k: (PAYLOAD if isinstance(v, str) else v) for k, v in it["extra"].items()}
            for s in d["sources"]:
                s["label"] = PAYLOAD
            d["eligibility"][0]["reason"] = PAYLOAD
            d["eligibility"][0]["requirements"][0]["evidence"]["quote"] = PAYLOAD
            d["eligibility"][0]["requirements"][0]["text"] = PAYLOAD
        self.put_today(mutate)
        html = self.html()
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x onerror=alert(7)&gt;", html)

    def test_quote_characters_cannot_break_out_of_attributes(self):
        def mutate(d):
            d["items"][0]["id"] = '"><script>alert(1)</script>'
            d["items"][0]["url"] = 'https://example.go.kr/"onmouseover="alert(1)'
        self.put_today(mutate)
        html = self.html()
        self.assertNotIn('"><script>alert(1)', html)
        self.assertNotIn('onmouseover="alert', html)


class DangerousLinks(ReportCase):
    def test_non_http_schemes_are_shown_as_text_not_links(self):
        bad = ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,<b>x</b>", "ftp://example.com/a", "//evil.example/x", ""]
        def mutate(d):
            for it, u in zip(d["items"], bad):
                it["url"] = u
            d["eligibility"][0]["unreadable_files"][0]["url"] = "javascript:alert(2)"
        self.put_today(mutate)
        html = self.html()
        for needle in ('href="javascript', 'href="JaVa', 'href="data:', 'href="ftp:', 'href="//', 'href=""'):
            self.assertNotIn(needle, html)
        self.assertIn("링크 없음", html)
        self.assertIn("AI 기반 3D 애니메이션 제작 용역", html)  # 항목 자체는 그대로 보인다
