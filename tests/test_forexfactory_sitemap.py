from datetime import date

from src.scrapper import forexfactory_sitemap as sitemap


def test_parse_sitemap_index():
    xml = """
    <sitemapindex>
      <sitemap>
        <loc>https://www.forexfactory.com/sitemap-1.xml</loc>
      </sitemap>
      <sitemap>
        <loc>https://www.forexfactory.com/sitemap-2.xml</loc>
      </sitemap>
    </sitemapindex>
    """
    urls = sitemap.parse_sitemap_index(xml)
    assert len(urls) == 2
    assert urls[0].endswith("sitemap-1.xml")


def test_parse_child_sitemap_and_date_parsing():
    xml = """
    <urlset>
      <url>
        <loc>https://www.forexfactory.com/event/1</loc>
        <lastmod>2026-05-10</lastmod>
      </url>
      <url>
        <loc>https://www.forexfactory.com/event/2</loc>
        <lastmod>2026-05-12T12:00:00Z</lastmod>
      </url>
    </urlset>
    """
    records = sitemap.parse_child_sitemap(xml)
    assert len(records) == 2
    assert records[0]["lastmod"] == date(2026, 5, 10)
    assert records[1]["lastmod"] == date(2026, 5, 12)


def test_get_sitemap_urls_filters(monkeypatch):
    index_xml = """
    <sitemapindex>
      <sitemap>
        <loc>https://www.forexfactory.com/sitemap-1.xml</loc>
      </sitemap>
    </sitemapindex>
    """

    child_xml = """
    <urlset>
      <url>
        <loc>https://www.forexfactory.com/event/old</loc>
        <lastmod>2020-01-01</lastmod>
      </url>
      <url>
        <loc>https://www.forexfactory.com/event/new</loc>
        <lastmod>2026-05-15</lastmod>
      </url>
    </urlset>
    """

    def fake_fetch(url, timeout=10):
        if "sitemap-index" in url:
            return index_xml
        return child_xml

    monkeypatch.setattr(sitemap, "fetch_url_text", fake_fetch)

    res = sitemap.get_sitemap_urls(
        start_date=date(2026, 5, 1), end_date=date(2026, 5, 31)
    )
    assert res["total"] == 1
    assert res["results"][0]["url"].endswith("/event/new")
