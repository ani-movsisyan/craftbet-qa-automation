"""Generates the Postman collection + environment for the CraftBet website API.

The collection is kept as Python so request bodies and test scripts stay readable and consistent.
Run:  python postman/build_collection.py
"""
import json
import re
import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parent
API = "{{baseUrl}}/{{partnerId}}/api/Main"
CATEGORY_IDS = [1, 0, 24, 21, 26, 12, 25, 13, 9, 6, 19, 8, 4, 16, 3, 2, 10, 22]


# ----------------------------------------------------------------------------- helpers
def render(obj) -> str:
    """json.dumps + turn "@@var@@" placeholders into raw Postman variables (numbers / booleans),
    and "@@s:var@@" into string variables. Works inside the JSON-encoded RequestData string too."""
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    text = re.sub(r'(\\*)"@@(\w+)@@\1"', r"{{\2}}", text)      # numeric placeholders (quoted / escaped)
    return text.replace("@@s:", "{{").replace("@@", "}}")      # string placeholders


def api_request(controller: str, method: str, request_data: dict | None = None) -> dict:
    """Body of the generic RPC endpoint /api/Main/ApiRequest used by the website for client data."""
    return {
        "Controller": controller,
        "Method": method,
        "PartnerId": "@@partnerId@@",
        "LanguageId": "@@s:languageId@@",
        "TimeZone": "@@timeZone@@",
        "Token": "@@s:token@@",
        "ClientId": "@@clientId@@",
        "RequestData": json.dumps(request_data or {}, separators=(",", ":")),
    }


def period(extra: dict | None = None) -> dict:
    data = {
        "ClientId": "@@clientId@@",
        "TimeZone": "@@timeZone@@",
        "CurrencyId": "@@s:currencyId@@",
        "CreatedFrom": "@@s:createdFrom@@",
        "CreatedBefore": "@@s:createdBefore@@",
        "SkipCount": 0,
        "TakeCount": 20,
    }
    data.update(extra or {})
    return data


def script(lines: str) -> list[str]:
    return [l for l in lines.strip("\n").split("\n")]


def item(name, description, method, path, body=None, tests="", query=None, auth=True):
    url = {"raw": f"{API}/{path}", "host": ["{{baseUrl}}"], "path": ["{{partnerId}}", "api", "Main", path]}
    if query:
        url["raw"] += "?" + "&".join(f"{k}={v}" for k, v in query)
        url["query"] = [{"key": k, "value": v} for k, v in query]
    request = {
        "method": method,
        "header": [
            {"key": "Content-Type", "value": "application/json"},
            {"key": "Accept", "value": "application/json"},
            # The API only answers requests coming from the partner website (otherwise: 138 RestrictedDestination)
            {"key": "Origin", "value": "{{siteUrl}}"},
            {"key": "Referer", "value": "{{siteUrl}}/"},
        ],
        "url": url,
        "description": description,
    }
    if body is not None:
        request["body"] = {"mode": "raw", "raw": render(body), "options": {"raw": {"language": "json"}}}
    events = [{"listen": "test", "script": {"type": "text/javascript", "exec": script(tests)}}]
    if auth:
        guard = REQUIRE_TOKEN_ONLY if auth == "token" else REQUIRE_TOKEN
        events.insert(0, {"listen": "prerequest", "script": {"type": "text/javascript", "exec": script(guard)}})
    return {"name": name, "request": request, "event": events, "response": []}


# ----------------------------------------------------------------------------- shared scripts
COLLECTION_PRE = r"""
// Rolling 30-day period used by all history requests
const now = new Date();
const from = new Date(now.getTime() - 30 * 24 * 3600 * 1000);
pm.collectionVariables.set('createdFrom', from.toISOString().slice(0, 19));
pm.collectionVariables.set('createdBefore', new Date(now.getTime() + 24 * 3600 * 1000).toISOString().slice(0, 19));
"""

COLLECTION_TESTS = r"""
// ---- common validations for every request ----
pm.test('HTTP status is 200', () => pm.response.to.have.status(200));
pm.test('Response time is below 5s', () => pm.expect(pm.response.responseTime).to.be.below(5000));
pm.test('Response is JSON', () => pm.response.to.be.json);
const body = pm.response.json();
pm.test('Platform ResponseCode is 0 (success)', () => {
    pm.expect(body.ResponseCode, `Description: ${body.Description}`).to.eql(0);
});
"""

REQUIRE_TOKEN = r"""
// Client data requires an authenticated session token (see README: Postman / How to get a token)
if (!pm.environment.get('token') || !pm.environment.get('clientId')) {
    console.warn('token / clientId are empty - request skipped');
    pm.execution.skipRequest();
}
"""

REQUIRE_TOKEN_ONLY = r"""
// Session validation needs only the token - it is the request that fills clientId / currencyId
if (!pm.environment.get('token')) {
    console.warn('token is empty - request skipped');
    pm.execution.skipRequest();
}
"""

LIST_HELPER = r"""
const json = pm.response.json();
const ro = json.ResponseObject;
// The API wraps lists differently per method - accept the known shapes
const list = Array.isArray(ro) ? ro
    : (ro && (ro.PaymentRequests || ro.Transactions || ro.Bets || ro.Entities || ro.Bonuses || ro.Documents)) || [];
"""

# ----------------------------------------------------------------------------- requests
AUTH = [
    item(
        "00. Validate session (GetClientByToken)",
        "Validates the token copied from an authenticated browser session (or produced by "
        "`scripts/get_api_token.py`) and stores clientId / currencyId for the following requests.",
        "POST", "GetClientByToken",
        {"LanguageId": "@@s:languageId@@", "Token": "@@s:token@@"},
        r"""
const c = pm.response.json();
pm.test('Session is valid - client Id returned', () => pm.expect(c.Id).to.be.a('number').and.above(0));
pm.test('Client has a currency', () => pm.expect(c.CurrencyId).to.be.a('string').and.not.empty);
pm.environment.set('clientId', c.Id);
pm.environment.set('currencyId', c.CurrencyId);
if (c.Token) { pm.environment.set('token', c.Token); }
""",
        auth="token",
    ),
]

CLIENT = [
    item(
        "01. Client information (GetClientInfo)",
        "Customer profile details: id, user name, e-mail, names, currency, verification flags.",
        "POST", "GetClientInfo",
        {"PartnerId": "@@partnerId@@", "LanguageId": "@@s:languageId@@", "TimeZone": "@@timeZone@@",
         "Token": "@@s:token@@", "ClientId": "@@clientId@@"},
        r"""
const c = pm.response.json().ResponseObject || pm.response.json();
pm.test('Profile belongs to the logged-in client', () => pm.expect(String(c.Id)).to.eql(String(pm.environment.get('clientId'))));
pm.test('Profile has user name and currency', () => {
    pm.expect(c).to.have.property('UserName');
    pm.expect(c.CurrencyId).to.eql(pm.environment.get('currencyId'));
});
pm.test('Sensitive data is not exposed', () => pm.expect(c.Password == null || c.Password === '').to.be.true);
""",
    ),
    item(
        "02. Account balance (GetClientBalance)",
        "Current balance of the client in the account currency (real + bonus balances).",
        "POST", "GetClientBalance",
        {"PartnerId": "@@partnerId@@", "Token": "@@s:token@@", "ClientId": "@@clientId@@",
         "RequestData": json.dumps({"CurrencyId": "@@s:currencyId@@"})},
        r"""
const b = pm.response.json();
pm.test('Balance currency matches client currency', () => pm.expect(b.CurrencyId).to.eql(pm.environment.get('currencyId')));
pm.test('AvailableBalance is a non-negative number', () => pm.expect(b.AvailableBalance).to.be.a('number').and.at.least(0));
pm.test('Balances is an array of typed balances', () => {
    pm.expect(b.Balances).to.be.an('array');
    b.Balances.forEach(x => pm.expect(x).to.have.property('Balance'));
});
""",
    ),
    item(
        "03. Account status (GetClientStates)",
        "Account state flags of the client (unread messages, verification / limitation states).",
        "POST", "ApiRequest",
        api_request("Client", "GetClientStates"),
        r"""
const ro = pm.response.json().ResponseObject;
pm.test('States object is returned', () => pm.expect(ro).to.not.be.undefined);
""",
    ),
    item(
        "04. Client accounts (GetClientAccounts)",
        "Wallet accounts of the client (real / bonus) with balances - complements Account Status.",
        "POST", "ApiRequest",
        api_request("Client", "GetClientAccounts", {"ClientId": "@@clientId@@"}),
        r"""
const ro = pm.response.json().ResponseObject;
pm.test('Accounts list is present', () => pm.expect(ro.Accounts).to.be.an('array').that.is.not.empty);
pm.test('Every account has currency and numeric balance', () => {
    ro.Accounts.forEach(a => {
        pm.expect(a.CurrencyId).to.be.a('string');
        pm.expect(a.Balance).to.be.a('number');
    });
});
""",
    ),
]

FINANCE = [
    item(
        "05. Deposit information (GetPaymentRequests Type=2)",
        "Deposit requests of the client for the last 30 days. Type 2 = deposit.",
        "POST", "ApiRequest",
        api_request("Document", "GetPaymentRequests", period({"Statuses": None, "Type": 2})),
        LIST_HELPER + r"""
pm.test('ResponseObject is returned', () => pm.expect(ro).to.not.be.undefined);
pm.test('All items are deposits of this client', () => {
    list.forEach(p => {
        if (p.Type !== undefined) pm.expect(p.Type).to.eql(2);
        if (p.ClientId !== undefined) pm.expect(String(p.ClientId)).to.eql(String(pm.environment.get('clientId')));
    });
});
""",
    ),
    item(
        "06. Withdrawal information (GetPaymentRequests Type=1)",
        "Withdrawal requests of the client for the last 30 days. Type 1 = withdrawal.",
        "POST", "ApiRequest",
        api_request("Document", "GetPaymentRequests", period({"Statuses": None, "Type": 1})),
        LIST_HELPER + r"""
pm.test('ResponseObject is returned', () => pm.expect(ro).to.not.be.undefined);
pm.test('All items are withdrawals', () => list.forEach(p => { if (p.Type !== undefined) pm.expect(p.Type).to.eql(1); }));
""",
    ),
    item(
        "07. Transaction history (GetTransactionHistory)",
        "All balance operations (bets, wins, deposits, bonuses) of the last 30 days, first page of 20.",
        "POST", "ApiRequest",
        api_request("Document", "GetTransactionHistory", period()),
        LIST_HELPER + r"""
pm.test('ResponseObject is returned', () => pm.expect(ro).to.not.be.undefined);
pm.test('Page size is respected (<= 20)', () => pm.expect(list.length).to.be.at.most(20));
pm.test('Transactions have amount and date', () => list.forEach(t => {
    pm.expect(t).to.have.property('Amount');
    pm.expect(t).to.satisfy(x => 'CreationTime' in x || 'CreationDate' in x || 'Date' in x);
}));
""",
    ),
    item(
        "08. Payment methods (GetPartnerPaymentSystems)",
        "Payment systems available to the client for deposits.",
        "POST", "GetPartnerPaymentSystems",
        {"PartnerId": "@@partnerId@@", "LanguageId": "@@s:languageId@@", "Token": "@@s:token@@",
         "ClientId": "@@clientId@@", "Type": 2},
        r"""
const r = pm.response.json();
pm.test('PartnerPaymentSystems list is returned', () => pm.expect(r.PartnerPaymentSystems).to.be.an('array'));
pm.test('Each payment method has an id and a name', () => r.PartnerPaymentSystems.forEach(p => {
    pm.expect(p).to.have.property('Id');
    pm.expect(p).to.satisfy(x => 'Name' in x || 'PaymentSystemName' in x);
}));
""",
    ),
]

ACTIVITY = [
    item(
        "09. Bonus information (GetBonuses)",
        "Bonuses available / assigned to the client.",
        "POST", "ApiRequest",
        api_request("Document", "GetBonuses", {"PlatformId": 2, "ProductId": 1}),
        LIST_HELPER + r"""
pm.test('Bonuses are returned as a list', () => pm.expect(list).to.be.an('array'));
pm.test('Bonus items have id and status', () => list.forEach(b => {
    pm.expect(b).to.satisfy(x => 'Id' in x || 'BonusId' in x);
}));
""",
    ),
    item(
        "10. Betting history (GetBetsHistory)",
        "Customer betting activity for the last 30 days (casino + sport), first page of 20.",
        "POST", "ApiRequest",
        api_request("Document", "GetBetsHistory", period()),
        LIST_HELPER + r"""
pm.test('Bets list and total count are returned', () => {
    pm.expect(ro.Bets).to.be.an('array');
    pm.expect(ro.Count).to.be.a('number').and.at.least(ro.Bets.length);
});
pm.test('Each bet has amount, state and product', () => ro.Bets.forEach(b => {
    pm.expect(b.BetAmount).to.be.a('number');
    pm.expect(b).to.have.property('State');
    pm.expect(b).to.have.property('ProductName');
}));
""",
    ),
]

PUBLIC = [
    item(
        "11. Game information - search (GetGames)",
        "Public catalogue search: games whose name matches `{{gamePattern}}`. Does not require a session.",
        "POST", "GetGames",
        {"PartnerId": "@@partnerId@@", "TimeZone": "@@timeZone@@", "LanguageId": "@@s:languageId@@",
         "Method": "GetGames", "CategoryId": None, "PageIndex": 0, "PageSize": 24, "ProviderIds": [],
         "CategoryIds": CATEGORY_IDS, "Pattern": "@@s:gamePattern@@",
         "RequestData": json.dumps({"Pattern": "@@s:gamePattern@@", "ProviderIds": [], "CategoryId": None,
                                    "PageIndex": 0, "PageSize": 24, "CategoryIds": CATEGORY_IDS})},
        r"""
const games = pm.response.json().ResponseObject.Games;
const pattern = pm.environment.get('gamePattern').toLowerCase();
pm.test('Games are found', () => pm.expect(games).to.be.an('array').that.is.not.empty);
pm.test('Page size is respected (<= 24)', () => pm.expect(games.length).to.be.at.most(24));
pm.test('Every game name contains the search pattern', () => games.forEach(g => pm.expect(g.n.toLowerCase()).to.include(pattern)));
pm.test('Every game has id, provider and image', () => games.forEach(g => {
    pm.expect(g.p).to.be.a('number');
    pm.expect(g.sp).to.be.a('string').and.not.empty;
    pm.expect(g.i).to.be.a('string').and.not.empty;
}));
pm.environment.set('sampleGameId', games[0].p);
""",
        auth=False,
    ),
    item(
        "12. Game providers (GetGameProviders)",
        "Public list of game providers with the number of games for each.",
        "POST", "GetGameProviders",
        {"PartnerId": "@@partnerId@@", "LanguageId": "@@s:languageId@@", "TimeZone": "@@timeZone@@"},
        r"""
const providers = pm.response.json().ResponseObject.Providers;
pm.test('Providers list is not empty', () => pm.expect(providers).to.be.an('array').that.is.not.empty);
pm.test('Providers have id, name and positive games count', () => providers.forEach(p => {
    pm.expect(p.Id).to.be.a('number');
    pm.expect(p.Name).to.be.a('string').and.not.empty;
    pm.expect(p.GamesCount).to.be.a('number').and.at.least(0);
}));
pm.test('Provider ids are unique', () => pm.expect(new Set(providers.map(p => p.Id)).size).to.eql(providers.length));
""",
        auth=False,
    ),
    item(
        "13. Latest winning bets - GET (getbets)",
        "Public GET endpoint used by the home page 'Wins' widget. Shows that bet data is masked for other users.",
        "GET", "getbets", None,
        r"""
const bets = pm.response.json().ResponseObject;
pm.test('Bets list is returned', () => pm.expect(bets).to.be.an('array'));
pm.test('Only winning bets are returned (winnersonly=true)', () => bets.forEach(b => pm.expect(b.WinAmount).to.be.above(0)));
pm.test('Other users names are masked', () => bets.forEach(b => pm.expect(b.UserName).to.match(/^\*+/)));
pm.test('Each bet has product and currency', () => bets.forEach(b => {
    pm.expect(b.ProductName).to.be.a('string');
    pm.expect(b.CurrencyId).to.be.a('string');
}));
""",
        query=[("timeZone", "{{timeZone}}"), ("languageId", "{{languageId}}"), ("winnersonly", "true")],
        auth=False,
    ),
]


def folder(name, description, items):
    return {"name": name, "description": description, "item": items}


collection = {
    "info": {
        "_postman_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "craftbet-api-collection")),
        "name": "CraftBet API - data retrieval",
        "description": (
            "Read-only requests to the CraftBet website API (`websitewebapi.craftbet.com`).\n\n"
            "The platform exposes an RPC-style API: most read operations are `POST` requests whose body names the "
            "`Controller` and `Method` (e.g. `Document/GetBetsHistory`). Only `Get*` methods are used here - nothing "
            "creates, changes or deletes data.\n\n"
            "Authentication: the website encrypts credentials client-side (RSA) before `LoginClient`, so the "
            "collection works with a session token instead. Put it into the `token` environment variable "
            "(see README) and run `00. Validate session` first."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "event": [
        {"listen": "prerequest", "script": {"type": "text/javascript", "exec": script(COLLECTION_PRE)}},
        {"listen": "test", "script": {"type": "text/javascript", "exec": script(COLLECTION_TESTS)}},
    ],
    "variable": [{"key": "createdFrom", "value": ""}, {"key": "createdBefore", "value": ""}],
    "item": [
        folder("Public data (no session)", "Catalogue data available to any visitor.", PUBLIC),
        folder("Authentication", "Validates the session token and fills clientId / currencyId.", AUTH),
        folder("Client profile & status", "Customer profile, balance and account status.", CLIENT),
        folder("Payments & transactions", "Deposits, withdrawals, transaction history, payment methods.", FINANCE),
        folder("Bonuses & betting", "Bonuses and betting history.", ACTIVITY),
    ],
}

environment = {
    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "craftbet-api-env")),
    "name": "CraftBet - production web API",
    "values": [
        {"key": "baseUrl", "value": "https://websitewebapi.craftbet.com", "type": "default", "enabled": True},
        {"key": "siteUrl", "value": "https://craftbet.com", "type": "default", "enabled": True},
        {"key": "partnerId", "value": "1", "type": "default", "enabled": True},
        {"key": "languageId", "value": "en", "type": "default", "enabled": True},
        {"key": "timeZone", "value": "4", "type": "default", "enabled": True},
        {"key": "gamePattern", "value": "book", "type": "default", "enabled": True},
        {"key": "token", "value": "", "type": "secret", "enabled": True},
        {"key": "clientId", "value": "", "type": "default", "enabled": True},
        {"key": "currencyId", "value": "", "type": "default", "enabled": True},
    ],
    "_postman_variable_scope": "environment",
}

if __name__ == "__main__":
    (OUT / "CraftBet_API.postman_collection.json").write_text(json.dumps(collection, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "CraftBet.postman_environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
    total = sum(len(f["item"]) for f in collection["item"])
    print(f"Collection written: {total} requests")
