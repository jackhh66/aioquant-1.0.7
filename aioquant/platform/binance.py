# -*- coding:utf-8 -*-

"""
Binance Trade module.
https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md

Author: HuangTao
Date:   2018/08/09
Email:  huangtao@ifclover.com
"""

import hashlib
import hmac
from urllib.parse import urljoin

from aioquant.utils import tools
from aioquant.utils.web import AsyncHttpRequests

__all__ = ("BinanceRestAPI", )


class BinanceRestAPI:
    """Binance REST API client.

    Attributes:
        access_key: Account's ACCESS KEY.
        secret_key: Account's SECRET KEY.
        host: HTTP request host, default `https://api.binance.com`.
    """

    def __init__(self, access_key, secret_key, host=None):
        """Initialize REST API client."""
        self._host = host or "https://api.binance.com"
        self._access_key = access_key
        self._secret_key = secret_key

    async def ping(self):
        """Test connectivity.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/ping"
        success, error = await self.request("GET", uri)
        return success, error

    async def get_server_time(self):
        """Get server time.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/time"
        success, error = await self.request("GET", uri)
        return success, error

    async def get_exchange_info(self):
        """Get exchange information.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/exchangeInfo"
        success, error = await self.request("GET", uri)
        return success, error

    async def get_orderbook(self, symbol, limit=10):
        """Get latest orderbook information.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            limit: Number of results per request. (default 10, max 5000.)

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/depth"
        params = {
            "symbol": symbol,
            "limit": limit
        }
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_trade(self, symbol, limit=500):
        """Get latest trade information.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            limit: Number of results per request. (Default 500, max 1000.)

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/trades"
        params = {
            "symbol": symbol,
            "limit": limit
        }
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_kline(self, symbol, interval="1m", start=None, end=None, limit=500):
        """Get kline information.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            interval: Kline interval type, valid values: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            start: Start timestamp(millisecond).
            end: End timestamp(millisecond).
            limit: Number of results per request. (Default 500, max 1000.)

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Notes:
            If start and end are not sent, the most recent klines are returned.
        """
        uri = "/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        if start and end:
            params["startTime"] = start
            params["endTime"] = end
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_average_price(self, symbol):
        """Current average price for a symbol.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/avgPrice"
        params = {
            "symbol": symbol
        }
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_user_account(self):
        """Get user account information.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/account"
        ts = tools.get_cur_timestamp_ms()
        params = {
            "timestamp": str(ts)
        }
        success, error = await self.request("GET", uri, params, auth=True)
        return success, error

    async def create_order(self, action, symbol, price, quantity, client_order_id=None):
        """Create an order.
        Args:
            action: Trade direction, `BUY` or `SELL`.
            symbol: Symbol name, e.g. `BTCUSDT`.
            price: Price of each contract.
            quantity: The buying or selling quantity.
            client_order_id: Client order id.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/order"
        data = {
            "symbol": symbol,
            "side": action,
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": quantity,
            "price": price,
            "recvWindow": "5000",
            "newOrderRespType": "FULL",
            "timestamp": tools.get_cur_timestamp_ms()
        }
        if client_order_id:
            data["newClientOrderId"] = client_order_id
        success, error = await self.request("POST", uri, body=data, auth=True)
        return success, error

    async def revoke_order(self, symbol, order_id, client_order_id=None):
        """Cancelling an unfilled order.
        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            order_id: Order id.
            client_order_id: Client order id.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/order"
        params = {
            "symbol": symbol,
            "orderId": order_id,
            "timestamp": tools.get_cur_timestamp_ms()
        }
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        success, error = await self.request("DELETE", uri, params=params, auth=True)
        return success, error

    async def get_order_status(self, symbol, order_id, client_order_id):
        """Get order details by order id.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            order_id: Order id.
            client_order_id: Client order id.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/order"
        params = {
            "symbol": symbol,
            "orderId": str(order_id),
            "origClientOrderId": client_order_id,
            "timestamp": tools.get_cur_timestamp_ms()
        }
        success, error = await self.request("GET", uri, params=params, auth=True)
        return success, error

    async def get_all_orders(self, symbol):
        """Get all account orders; active, canceled, or filled.
        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/allOrders"
        params = {
            "symbol": symbol,
            "timestamp": tools.get_cur_timestamp_ms()
        }
        success, error = await self.request("GET", uri, params=params, auth=True)
        return success, error

    async def get_open_orders(self, symbol):
        """Get all open order information.
        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/openOrders"
        params = {
            "symbol": symbol,
            "timestamp": tools.get_cur_timestamp_ms()
        }
        success, error = await self.request("GET", uri, params=params, auth=True)
        return success, error

    async def get_listen_key(self):
        """Get listen key, start a new user data stream.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/userDataStream"
        success, error = await self.request("POST", uri)
        return success, error

    async def put_listen_key(self, listen_key):
        """Keepalive a user data stream to prevent a time out.

        Args:
            listen_key: Listen key.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/userDataStream"
        params = {
            "listenKey": listen_key
        }
        success, error = await self.request("PUT", uri, params=params)
        return success, error

    async def delete_listen_key(self, listen_key):
        """Delete a listen key.

        Args:
            listen_key: Listen key.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/userDataStream"
        params = {
            "listenKey": listen_key
        }
        success, error = await self.request("DELETE", uri, params=params)
        return success, error

    async def request(self, method, uri, params=None, body=None, headers=None, auth=False):
        """Do HTTP request.

        Args:
            method: HTTP request method. `GET` / `POST` / `DELETE` / `PUT`.
            uri: HTTP request uri.
            params: HTTP query params.
            body:   HTTP request body.
            headers: HTTP request headers.
            auth: If this request requires authentication.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        url = urljoin(self._host, uri)
        data = {}
        if params:
            data.update(params)
        if body:
            data.update(body)

        if data:
            query = "&".join(["=".join([str(k), str(v)]) for k, v in data.items()])
        else:
            query = ""
        if auth and query:
            signature = hmac.new(self._secret_key.encode(), query.encode(), hashlib.sha256).hexdigest()
            query += "&signature={s}".format(s=signature)
        if query:
            url += ("?" + query)

        if not headers:
            headers = {}
        headers["X-MBX-APIKEY"] = self._access_key
        _, success, error = await AsyncHttpRequests.fetch(method, url, headers=headers, timeout=10, verify_ssl=False)
        return success, error
