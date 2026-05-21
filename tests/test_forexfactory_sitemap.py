from datetime import date

from src.scrapper import forexfactory_sitemap as sitemap


def test_parse_sitemap_index():
    # Test with namespace (real-world format)
    xml = """
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
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

    # Test without namespace (fallback)
    xml_no_ns = """
    <sitemapindex>
      <sitemap>
        <loc>https://www.forexfactory.com/sitemap-3.xml</loc>
      </sitemap>
    </sitemapindex>
    """
    urls_no_ns = sitemap.parse_sitemap_index(xml_no_ns)
    assert len(urls_no_ns) == 1


def test_parse_child_sitemap_and_date_parsing():
    # Test with namespace (real-world format)
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
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
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap>
        <loc>https://www.forexfactory.com/sitemap-1.xml</loc>
      </sitemap>
    </sitemapindex>
    """

    child_xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
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


def test_sitemaps_route_with_date_filter(monkeypatch):
    """Test the Flask route /api/forex/sitemaps with date filtering."""
    from src.app import app

    index_xml = """
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap>
        <loc>https://www.forexfactory.com/sitemap-calendar.xml</loc>
      </sitemap>
    </sitemapindex>
    """

    child_xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url>
        <loc>https://www.forexfactory.com/calendar/2020</loc>
        <lastmod>2020-01-01</lastmod>
      </url>
      <url>
        <loc>https://www.forexfactory.com/calendar/2026</loc>
        <lastmod>2026-05-15</lastmod>
      </url>
    </urlset>
    """

    def fake_fetch(url, timeout=10):
        if "sitemap-index" in url:
            return index_xml
        return child_xml

    monkeypatch.setattr(sitemap, "fetch_url_text", fake_fetch)

    client = app.test_client()
    res = client.get("/api/forex/sitemaps?start_date=2026-05-01&end_date=2026-05-31")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] == 1
    assert data["results"][0]["url"].endswith("/calendar/2026")


def test_sitemaps_route_invalid_date_format(monkeypatch):
    """Test that invalid date format returns 400."""
    from src.app import app

    client = app.test_client()
    res = client.get("/api/forex/sitemaps?start_date=invalid-date")
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data


def test_sitemaps_route_invalid_max_pages(monkeypatch):
    """Test that invalid max_pages returns 400."""
    from src.app import app

    client = app.test_client()
    res = client.get("/api/forex/sitemaps?max_pages=invalid")
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data
