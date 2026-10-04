"""Kursy walut z API NBP (darmowe, bez klucza)."""

import httpx

NBP_URL = "https://api.nbp.pl/api/exchangerates/rates/a/{code}/"


async def get_rate(http: httpx.AsyncClient, code: str) -> str:
    code = code.strip().upper()
    if code == "PLN":
        return "1 PLN = 1 PLN, szefie."
    if len(code) != 3 or not code.isalpha():
        return f"'{code}' to nie jest kod waluty (np. EUR, USD, GBP)."
    resp = await http.get(NBP_URL.format(code=code.lower()), params={"format": "json"})
    if resp.status_code == 404:
        return f"NBP nie podaje kursu dla {code}."
    resp.raise_for_status()
    data = resp.json()
    rate = data["rates"][0]
    return f"1 {code} = {rate['mid']} PLN (kurs średni NBP z {rate['effectiveDate']})."
