"""Set curated ja/en/zh-TW/zh-CN listings on each unique site adapter."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from japan_events.langs import SCRAPE_LANGS  # noqa: E402

# Official prefecture 観光協会 / DMO event listings per UI language.
# Sister inbound portals are used only when the Japanese association site
# has no matching calendar in that language.
URLS: dict[str, dict[str, str]] = {
    "hokkaido": {
        "en": "https://www.visit-hokkaido.jp/en/event/",
        "ja": "https://www.visit-hokkaido.jp/event/",
        "zh-TW": "https://www.visit-hokkaido.jp/tw/event/",
        "zh-CN": "https://www.visit-hokkaido.jp/cn/event/",
    },
    "aomori": {
        "en": "https://aomori-tourism.com/en/event/index.html",
        "ja": "https://aomori-tourism.com/event/index.html",
        "zh-TW": "https://aomori-tourism.com/tw/event/index.html",
        "zh-CN": "https://aomori-tourism.com/cn/event/index.html",
    },
    "iwate": {
        "en": "https://iwatetabi.jp/en/events/",
        "ja": "https://iwatetabi.jp/events/",
        "zh-TW": "https://iwatetabi.jp/tw/events/",
        "zh-CN": "https://iwatetabi.jp/cn/events/",
    },
    "miyagi": {
        "ja": "https://www.miyagi-kankou.or.jp/calendar/",
        "en": "https://visitmiyagi.com/events/",
        "zh-TW": "https://visitmiyagi.com/zh-hant/events/",
        "zh-CN": "https://visitmiyagi.com/zh-hans/events/",
    },
    "akita": {
        "ja": "https://akita-fun.jp/events",
        "en": "https://akita-fun.jp/en/events",
        "zh-TW": "https://stayakita.com/zh-tw/",
        "zh-CN": "https://stayakita.com/zh-cn/",
    },
    "yamagata": {
        "en": "https://yamagatakanko.com/en/festivals/",
        "ja": "https://yamagatakanko.com/festivals/",
        "zh-TW": "https://yamagatakanko.com/zh_TW/festivals/",
        "zh-CN": "https://yamagatakanko.com/zh_CN/festivals/",
    },
    "fukushima": {
        "ja": "https://www.tif.ne.jp/jp/entry/?type=event",
        "en": "https://fukushima.travel/en/events/",
        "zh-TW": "https://fukushima.travel/zh-tw/events/",
        "zh-CN": "https://fukushima.travel/zh-cn/events/",
    },
    "ibaraki": {
        "ja": "https://www.ibarakiguide.jp/event.php",
        "en": "https://www.ibarakiguide.jp/en/event.php",
        "zh-TW": "https://visit.ibarakiguide.jp/zh-hant/",
        "zh-CN": "https://visit.ibarakiguide.jp/zh-hans/",
    },
    "tochigi": {
        "ja": "https://www.tochigiji.or.jp/event/",
        "en": "https://www.visit-tochigi.com/seasons-in-tochigi/events/",
        "zh-TW": "https://www.visit-tochigi.com/zh-tw/",
        "zh-CN": "https://www.visit-tochigi.com/zh-cn/",
    },
    "gunma": {
        "ja": "https://gunma-kanko.jp/events",
        "en": "https://www.visit-gunma.jp/en/",
        "zh-TW": "https://www.visit-gunma.jp/tcn/",
        "zh-CN": "https://www.visit-gunma.jp/scn/",
    },
    "saitama": {
        "en": "https://saitama-supportdesk.com/events/",
        "ja": "https://saitama-supportdesk.com/ja/events/",
        "zh-TW": "https://saitama-supportdesk.com/zh-hant/events/",
        "zh-CN": "https://saitama-supportdesk.com/zh-hans/events/",
    },
    "chiba": {
        "ja": "https://maruchiba.jp/event/index.html",
        "en": "https://www.visitchiba.jp/en/event/",
        "zh-TW": "https://www.visitchiba.jp/zh-tw/event/",
        "zh-CN": "https://www.visitchiba.jp/zh-cn/event/",
    },
    "tokyo": {
        "en": "https://www.gotokyo.org/en/calendar/index.html",
        "ja": "https://www.gotokyo.org/jp/calendar/index.html",
        "zh-TW": "https://www.gotokyo.org/tc/calendar/index.html",
        "zh-CN": "https://www.gotokyo.org/cn/calendar/index.html",
    },
    "kanagawa": {
        "ja": "https://www.kanagawa-kankou.or.jp/event/",
        "en": "https://www.visitkanagawa.jp/en/events/",
        "zh-TW": "https://www.visitkanagawa.jp/zh-tw/",
        "zh-CN": "https://www.visitkanagawa.jp/zh-cn/",
    },
    "yamanashi": {
        "ja": "https://www.yamanashi-kankou.jp/search/event.php",
        "en": "https://www.yamanashi-kankou.jp/english/event/",
        "zh-TW": "https://www.yamanashi-kankou.jp/chinese_t/event/",
        "zh-CN": "https://www.yamanashi-kankou.jp/chinese_s/event/",
    },
    "nagano": {
        "en": "https://www.go-nagano.net/en/",
        "ja": "https://www.go-nagano.net/",
        "zh-TW": "https://www.go-nagano.net/tc/",
        "zh-CN": "https://www.go-nagano.net/sc/",
    },
    "niigata": {
        "en": "https://discover-niigata.com/events/",
        "ja": "https://niigata-kankou.or.jp/event/",
        "zh-TW": "https://enjoyniigata.com/zh-tw/",
        "zh-CN": "https://enjoyniigata.com/zh-cn/",
    },
    "toyama": {
        "ja": "https://www.info-toyama.com/events",
        "en": "https://visit-toyama-japan.com/en/events/",
        "zh-TW": "https://visit-toyama-japan.com/zh-TW/events/",
        "zh-CN": "https://visit-toyama-japan.com/zh-CN/events/",
    },
    "ishikawa": {
        "ja": "https://www.hot-ishikawa.jp/event/index.html",
        "en": "https://www.ishikawatravel.jp/en/event/",
        "zh-TW": "https://www.ishikawatravel.jp/tw/event/",
        "zh-CN": "https://www.ishikawatravel.jp/cn/event/",
    },
    "fukui": {
        "en": "https://www.fuku-e.com/en/events/index.html",
        "ja": "https://www.fuku-e.com/events/index.html",
        "zh-TW": "https://www.fuku-e.com/zh-TW/events/index.html",
        "zh-CN": "https://www.fuku-e.com/zh-CN/events/index.html",
    },
    "gifu": {
        "ja": "https://www.kankou-gifu.jp/event/",
        "en": "https://visitgifu.com/en/events/",
        "zh-TW": "https://visitgifu.com/tw/",
        "zh-CN": "https://visitgifu.com/cn/",
    },
    "shizuoka": {
        "ja": "https://www.visit-shizuoka.com/event/index.html",
        "en": "https://www.visit-shizuoka.com/en/event/index.html",
        "zh-TW": "https://www.visit-shizuoka.com/zh-tw/event/index.html",
        "zh-CN": "https://www.visit-shizuoka.com/zh-cn/event/index.html",
    },
    "aichi": {
        "en": "https://aichinow.pref.aichi.jp/en/events/",
        "ja": "https://aichinow.pref.aichi.jp/events/",
        "zh-TW": "https://aichinow.pref.aichi.jp/tw/events/",
        "zh-CN": "https://aichinow.pref.aichi.jp/cn/events/",
    },
    "mie": {
        "ja": "https://www.kankomie.or.jp/event",
        "en": "https://visitmie-japan.travel/en/events/",
        "zh-TW": "https://visitmie-japan.travel/tw/",
        "zh-CN": "https://visitmie-japan.travel/cn/",
    },
    "shiga": {
        "ja": "https://www.biwako-visitors.jp/event/",
        "en": "https://en.biwako-visitors.jp/event/",
        "zh-TW": "https://tw.biwako-visitors.jp/event/",
        "zh-CN": "https://cn.biwako-visitors.jp/event/",
    },
    "kyoto": {
        "en": "https://kyoto.travel/en/events/",
        "ja": "https://ja.kyoto.travel/events/",
        "zh-TW": "https://tw.kyoto.travel/events/",
        "zh-CN": "https://cn.kyoto.travel/events/",
    },
    "osaka": {
        "en": "https://osaka-info.jp/en/event/",
        "ja": "https://osaka-info.jp/event/",
        "zh-TW": "https://osaka-info.jp/tc/event/",
        "zh-CN": "https://osaka-info.jp/sc/event/",
    },
    "hyogo": {
        "ja": "https://www.hyogo-tourism.jp/event/index.html",
        "en": "https://www.hyogo-tourism.jp/en/event/",
        "zh-TW": "https://www.hyogo-tourism.jp/zh-TW/event/",
        "zh-CN": "https://www.hyogo-tourism.jp/zh-CN/event/",
    },
    "nara": {
        "en": "https://www.visitnara.jp/event-calendar/",
        "ja": "https://www.nara-kankou.or.jp/event/",
        "zh-TW": "https://www.visitnara.jp/zh-tw/event-calendar/",
        "zh-CN": "https://www.visitnara.jp/zh-cn/event-calendar/",
    },
    "wakayama": {
        "en": "https://visitwakayama.jp/en/events/index.html",
        "ja": "https://visitwakayama.jp/events/index.html",
        "zh-TW": "https://visitwakayama.jp/zh-TW/events/index.html",
        "zh-CN": "https://visitwakayama.jp/zh-CN/events/index.html",
    },
    "tottori": {
        "ja": "https://www.tottori-guide.jp/event/",
        "en": "https://www.tottori-tour.jp/en/event/",
        "zh-TW": "https://www.tottori-tour.jp/zh-tw/event/",
        "zh-CN": "https://www.tottori-tour.jp/zh-cn/event/",
    },
    "shimane": {
        "en": "https://www.kankou-shimane.com/en/destinations/?post_type=destinations&destination_spot%5B%5D=festival",
        "ja": "https://www.kankou-shimane.com/ja/destinations/?post_type=destinations&destination_spot%5B%5D=festival",
        "zh-TW": "https://www.kankou-shimane.com/zh-tw/activities",
        "zh-CN": "https://www.kankou-shimane.com/zh-cn/activities",
    },
    "okayama": {
        "en": "https://www.okayama-japan.jp/en/event",
        "ja": "https://www.okayama-japan.jp/event",
        "zh-TW": "https://www.okayama-japan.jp/tw/event",
        "zh-CN": "https://www.okayama-japan.jp/cn/event",
    },
    "hiroshima": {
        "en": "https://dive-hiroshima.com/en/events/",
        "ja": "https://dive-hiroshima.com/events/",
        "zh-TW": "https://dive-hiroshima.com/tw/events/",
        "zh-CN": "https://dive-hiroshima.com/cn/events/",
    },
    "yamaguchi": {
        "ja": "https://yamaguchi-tourism.jp/event/",
        "en": "https://www.visit-jy.com/en/",
        "zh-TW": "https://www.visit-jy.com/zh-tw/",
        "zh-CN": "https://www.visit-jy.com/zh-cn/",
    },
    "tokushima": {
        "ja": "https://www.awanavi.jp/event-calendar",
        "en": "https://discovertokushima.net/en/events/",
        "zh-TW": "https://discovertokushima.net/tw/",
        "zh-CN": "https://discovertokushima.net/cn/",
    },
    "kagawa": {
        "ja": "https://www.my-kagawa.jp/event/",
        "en": "https://www.my-kagawa.jp/en/event/",
        "zh-TW": "https://www.my-kagawa.jp/zh_TW/event/",
        "zh-CN": "https://www.my-kagawa.jp/zh_CN/event/",
    },
    "ehime": {
        "ja": "https://www.iyokannet.jp/event",
        "en": "https://www.visitehimejapan.com/en/",
        "zh-TW": "https://www.visitehimejapan.com/zh_TW",
        "zh-CN": "https://www.visitehimejapan.com/zh_CN",
    },
    "kochi": {
        "ja": "https://kochi-tabi.jp/search_event.html",
        "en": "https://visitkochijapan.com/en/highlights/event",
        "zh-TW": "https://visitkochijapan.com/tc/highlights/event",
        "zh-CN": "https://visitkochijapan.com/sc/highlights/event",
    },
    "fukuoka": {
        "en": "https://www.crossroadfukuoka.jp/en/event",
        "ja": "https://www.crossroadfukuoka.jp/event",
        "zh-TW": "https://www.crossroadfukuoka.jp/tw/event",
        "zh-CN": "https://www.crossroadfukuoka.jp/cn/event",
    },
    "saga": {
        "en": "https://www.saga-tripgenius.com/",
        "ja": "https://www.saga-tripgenius.com/ja/",
        "zh-TW": "https://www.saga-tripgenius.com/zh-hant/",
        "zh-CN": "https://www.saga-tripgenius.com/zh-hans/",
    },
    "nagasaki": {
        "ja": "https://www.nagasaki-tabinet.com/event",
        "en": "https://www.nagasaki-tabinet.com/en/event",
        "zh-TW": "https://www.discover-nagasaki.com/zh-TW",
        "zh-CN": "https://www.discover-nagasaki.com/zh-CN",
    },
    "kumamoto": {
        "en": "https://kumamoto-guide.jp/en/events/",
        "ja": "https://kumamoto-guide.jp/events/",
        "zh-TW": "https://kumamoto-guide.jp/tw/events/",
        "zh-CN": "https://kumamoto-guide.jp/zh/events/",
    },
    "oita": {
        "en": "https://www.visit-oita.jp/events/",
        "ja": "https://www.visit-oita.jp/ja/events/",
        "zh-TW": "https://oita-tourism.com/zh-TW",
        "zh-CN": "https://oita-tourism.com/zh-CN",
    },
    "miyazaki": {
        "ja": "https://www.kanko-miyazaki.jp/event",
        "en": "https://www.kanko-miyazaki.jp/en",
        "zh-TW": "https://www.kanko-miyazaki.jp/zh-tw",
        "zh-CN": "https://www.kanko-miyazaki.jp/zh-cn",
    },
    "kagoshima": {
        "en": "https://www.kagoshima-kankou.com/for/events",
        "ja": "https://www.kagoshima-kankou.com/event",
        "zh-TW": "https://www.kagoshima-kankou.com/tw/events",
        "zh-CN": "https://www.kagoshima-kankou.com/cn/events",
    },
    "okinawa": {
        "ja": "https://www.okinawastory.jp/event/list?from={date}&to={date}",
        "en": "https://www.okinawastory.jp/en/event/list?from={date}&to={date}",
        "zh-TW": "https://www.okinawastory.jp/zh-tw/event/list?from={date}&to={date}",
        "zh-CN": "https://www.okinawastory.jp/zh-cn/event/list?from={date}&to={date}",
    },
    "jnto": {
        "en": "https://www.japan.travel/en/events/",
        "ja": "https://www.japan.travel/jp/",
        "zh-TW": "https://www.japan.travel/tw/see-and-do/festivals-and-events/",
        "zh-CN": "https://www.japan-travel.cn/guide/festivals-and-events/",
    },
}


def upsert(site_id: str, urls: dict[str, str]) -> None:
    path = ROOT / "data" / "adapters" / f"{site_id}.yaml"
    text = path.read_text(encoding="utf-8")
    block = "urls_by_lang:\n" + "".join(f'  {lang}: "{urls[lang]}"\n' for lang in SCRAPE_LANGS)
    if re.search(r"^urls_by_lang:\n(?:  .+\n)+", text, flags=re.M):
        text = re.sub(r"^urls_by_lang:\n(?:  .+\n)+", block, text, count=1, flags=re.M)
    elif re.search(r"^event_url: .+$", text, flags=re.M):
        text = re.sub(r"^(event_url: .+)$", r"\1\n" + block.rstrip("\n"), text, count=1, flags=re.M)
    else:
        text = block + text
    path.write_text(text, encoding="utf-8")


def main() -> None:
    missing = [site for site in URLS if not (ROOT / "data" / "adapters" / f"{site}.yaml").exists()]
    if missing:
        raise SystemExit(f"missing adapter yaml: {missing}")
    extra = sorted(p.stem for p in (ROOT / "data" / "adapters").glob("*.yaml") if p.stem not in URLS)
    if extra:
        raise SystemExit(f"adapter yaml without curated langs: {extra}")
    for site_id, urls in URLS.items():
        upsert(site_id, urls)
        print(f"updated {site_id}")


if __name__ == "__main__":
    main()
