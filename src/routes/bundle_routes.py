from flask import Blueprint, request, jsonify
import logging

from .common_helpers import (
    _resolve_helpers,
    _validate_date_range_params,
    _validate_paging_params,
)

logger = logging.getLogger(__name__)

bundle_bp = Blueprint("bundle", __name__)


@bundle_bp.route("/api/bundle", methods=["GET"])
def get_economic_events_bundle():
    """Endpoint to scrape economic events from multiple sources within a date range.

    Query Parameters:
    - sources: (optional) Comma-separated list of sources. Default is 'forex'.
               Supported values: 'forex', 'crypto', 'metal', 'energy'
    - start_date: (required) Start date in ISO format (YYYY-MM-DD)
    - end_date: (required) End date in ISO format (YYYY-MM-DD)
    - limit: (optional) Maximum number of events to return per source
    - offset: (optional) Number of records to skip (applied per source)

    Response:
    A JSON object with combined events from all requested sources, with pagination info.
    """
    # 1. Parse and validate query parameters
    supported_sources = {"forex", "crypto", "metal", "energy"}
    sources_raw = request.args.getlist("sources")

    if not sources_raw:
        sources = ["forex"]
    else:
        # Handle both comma-separated string and multiple query params
        sources = []
        for s in sources_raw:
            # Split by comma in case it's a single comma-separated string
            sources.extend([x.strip().lower() for x in s.split(",")])

    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    # Optional paging parameters
    limit_param = request.args.get("limit")
    offset_param = request.args.get("offset")

    # 2. Validate date range
    if not start_date_str or not end_date_str:
        return (
            jsonify(
                {
                    "error": "Missing required parameters",
                    "message": "Both 'start_date' and 'end_date' are required in YYYY-MM-DD format.",
                }
            ),
            400,
        )

    date_err, start_date, end_date = _validate_date_range_params(
        start_date_str, end_date_str
    )
    if date_err:
        return jsonify({"error": "Invalid date parameters", "message": date_err}), 400

    # 3. Validate sources
    invalid_sources = set(sources) - supported_sources
    if invalid_sources:
        return (
            jsonify(
                {
                    "error": "Unsupported source detected",
                    "message": (
                        f"Supported sources are {sorted(list(supported_sources))}. "
                        f"Invalid: {sorted(list(invalid_sources))}"
                    ),
                }
            ),
            400,
        )

    # 4. Validate paging parameters
    limit, offset, paging_err = _validate_paging_params(limit_param, offset_param)
    if paging_err:
        return (
            jsonify({"error": "Invalid paging parameters", "message": paging_err}),
            400,
        )

    logger.info(
        f"Bundle request | Sources: {sources} | Date range: {start_date} to {end_date}"
    )

    try:
        # 5. Fetch data from each source
        all_combined_events = []
        source_results = {}

        for source in sources:
            try:
                source_events = []

                if source == "forex":
                    source_events = _fetch_from_date_range(
                        "src.scrapper.forexFactoryScrapper", start_date, end_date
                    )
                elif source == "crypto":
                    source_events = _fetch_from_date_range(
                        "src.scrapper.cryptoCraftScrapper", start_date, end_date
                    )
                elif source == "metal":
                    source_events = _fetch_from_date_range(
                        "src.scrapper.metalsMineScrapper", start_date, end_date
                    )
                elif source == "energy":
                    source_events = _fetch_from_date_range(
                        "src.scrapper.energyExchScrapper", start_date, end_date
                    )

                # Add source tag to each event for tracking
                for event in source_events:
                    if isinstance(event, dict):
                        event["_source"] = source

                source_results[source] = source_events
                all_combined_events.extend(source_events)

                logger.info(f"Fetched {len(source_events)} events from {source}")

            except Exception as e:
                logger.warning(f"Failed to fetch from {source}: {e}")
                source_results[source] = []

        # 6. Apply paging to combined results
        total = len(all_combined_events)

        # Apply offset
        if offset and offset > 0:
            if offset >= total:
                paged = []
            else:
                paged = all_combined_events[offset:]
        else:
            paged = all_combined_events[:]

        # Apply limit
        if limit is not None:
            paged = paged[:limit]

        # Wrap results with pagination metadata
        response_body = {
            "total": total,
            "offset": offset,
            "limit": limit,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "sources": sources,
            "source_breakdown": {
                source: len(source_results.get(source, [])) for source in sources
            },
            "results": paged,
        }

        return jsonify(response_body), 200

    except Exception as e:
        logger.exception(f"Bundle scraper error: {e}")
        return (
            jsonify(
                {
                    "error": "Internal server error",
                    "message": "An error occurred while scraping the target websites.",
                }
            ),
            500,
        )


def _fetch_from_date_range(scraper_module_path, start_date, end_date):
    """Fetch records from a scraper for each day in the date range.

    Args:
        scraper_module_path: Path to scraper module (e.g., 'src.scrapper.forexFactoryScrapper')
        start_date: datetime.date object for start
        end_date: datetime.date object for end

    Returns:
        List of records from all days in the range
    """
    try:
        get_records, get_url = _resolve_helpers(scraper_module_path)
    except Exception as e:
        logger.error(
            f"Failed to resolve scraper helpers for {scraper_module_path}: {e}"
        )
        return []

    if not get_records or not get_url:
        logger.error(f"Scraper helpers not available for {scraper_module_path}")
        return []

    from datetime import timedelta

    all_records = []
    current_date = start_date

    while current_date <= end_date:
        try:
            day = current_date.day
            month = current_date.month
            year = current_date.year

            url = get_url(day, month, year, "day")
            record_json = get_records(url)

            if isinstance(record_json, list):
                # Add date info to each record
                for record in record_json:
                    if isinstance(record, dict):
                        record["_date"] = str(current_date)
                all_records.extend(record_json)

        except Exception as e:
            logger.warning(
                f"Failed to fetch data for {current_date} from {scraper_module_path}: {e}"
            )

        current_date += timedelta(days=1)

    return all_records
