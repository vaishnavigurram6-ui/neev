# buildguard/tools/cost_estimation_tool.py
# Fixed: project/table names from config (no YOUR_PROJECT_ID placeholder);
# added completed-value estimate from metro_city_prices for live-LTV use.

from google.cloud import bigquery

from ..config import TBL_LOAN_HISTORY, TBL_METRO_PRICES

_bq = None
def _client():
    global _bq
    if _bq is None:
        _bq = bigquery.Client()
    return _bq


def estimate_construction_cost(plot_area_sqft: float, region: str,
                               location: str = "") -> dict:
    """Estimates construction cost, tenure, and completed market value.

    Args:
        plot_area_sqft: Built-up area in square feet.
        region: City name (e.g. 'Hyderabad').
        location: Optional locality (e.g. 'Kompally') for a locality-level
            median; falls back to the city median when absent or unmatched.
    Returns:
        dict with 'estimated_cost', 'estimated_tenure_months',
        'completed_value_estimate', 'value_basis'.
    """
    client = _client()

    q1 = f"""
        SELECT AVG(estimated_cost / plot_area_sqft) AS rate_per_sqft,
               AVG(estimated_tenure_months) AS avg_tenure
        FROM `{TBL_LOAN_HISTORY}`
        WHERE region = @region
    """
    row = list(client.query(q1, job_config=bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("region", "STRING", region)]
    )).result())[0]
    build_rate = row.rate_per_sqft or 2000  # documented fallback
    tenure = row.avg_tenure or 10

    q2 = f"""
        SELECT APPROX_QUANTILES(price / area, 2)[OFFSET(1)] AS median_ppsf,
               COUNT(*) AS n
        FROM `{TBL_METRO_PRICES}`
        WHERE LOWER(city) = LOWER(@city)
          AND (@loc = '' OR LOWER(location) LIKE CONCAT('%', LOWER(@loc), '%'))
    """
    vrow = list(client.query(q2, job_config=bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("city", "STRING", region),
            bigquery.ScalarQueryParameter("loc", "STRING", location),
        ]
    )).result())[0]

    if vrow.n and vrow.n >= 5:
        market_ppsf, basis = float(vrow.median_ppsf), f"{location or region} median ({vrow.n} listings)"
    else:
        # locality too thin — refetch city-wide
        vrow2 = list(client.query(q2, job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("city", "STRING", region),
                bigquery.ScalarQueryParameter("loc", "STRING", ""),
            ]
        )).result())[0]
        market_ppsf = float(vrow2.median_ppsf or build_rate * 1.5)
        basis = f"{region} city median ({vrow2.n} listings)"

    return {
        "estimated_cost": round(plot_area_sqft * build_rate, 2),
        "estimated_tenure_months": round(tenure, 1),
        "completed_value_estimate": round(plot_area_sqft * market_ppsf, 2),
        "value_basis": basis,
    }
