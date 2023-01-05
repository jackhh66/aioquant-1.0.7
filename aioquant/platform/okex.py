# -*- coding:utf-8 -*-

"""
OKEx Trade module.
https://www.okex.me/docs/zh/

Author: HuangTao
Date:   2019/01/19
Email:  huangtao@ifclover.com
"""

import base64
import hmac
import json
import time
from urllib.parse import urljoin

from aioquant.order import ORDER_ACTION_BUY
from aioquant.order import ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET
from aioquant.utils import logger
from aioquant.utils.web import AsyncHttpRequests

__all__ = ("OKExRestAPI", )


class OKExRestAPI:
    """ OKEx REST API client.

    Attributes:
        access_key: Account's ACCESS KEY.
        secret_key: Account's SECRET KEY.
        passphrase: API KEY Passphrase.
        host: HTTP request host, default `https://www.okex.com`
    """

    def __init__(self, access_key, secret_key, passphrase, host=None):
        """Initialize."""
        self._host = host or "https://www.okex.com"
        self._access_key = access_key
        self._secret_key = secret_key
        self._passphrase = passphrase

    async def get_orderbook(self, symbol, depth=None, limit=10):
        """Get latest orderbook information.

        Args:
            symbol: Symbol name, e.g. `BTC-USDT`.
            depth: Aggregation of the order book. e.g . 0.1, 0.001.
            limit: Number of results per request. (default 10, max 200.)

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/spot/v3/instruments/{symbol}/book".format(symbol=symbol)
        params = {
            "size": limit
        }
        if depth:
            params["depth"] = depth
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_trade(self, symbol, limit=10):
        """Get latest trade information.

        Args:
            symbol: Symbol name, e.g. `BTC-USDT`.
            limit: Number of results per request. (Default 10, max 60.)

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/spot/v3/instruments/{symbol}/trades".format(symbol=symbol)
        params = {
            "limit": limit
        }
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_kline(self, symbol, interval="60", start=None, end=None):
        """Get kline information.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            interval: Kline interval type, valid values: 60/180/300/900/1800/3600/7200/14400/21600/43200/86400/604800.
            start: Start time in ISO 8601. e.g. 2019-03-19T16:00:00.000Z
            end: End time in ISO 8601. e.g. 2019-03-19T16:00:00.000Z

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Notes:
            Both parameters will be ignored if either one of start or end are not provided. The last 200 records of
            data will be returned if the time range is not specified in the request.
        """
        uri = "/api/spot/v3/instruments/{symbol}/candles".format(symbol=symbol)
        params = {
            "granularity": interval
        }
        if start and end:
            params["start"] = start
            params["end"] = end
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_user_account(self):
        """Get account asset information.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/spot/v3/accounts"
        result, error = await self.request("GET", uri, auth=True)
        return result, error

    async def create_order(self, action, symbol, price, quantity, order_type=ORDER_TYPE_LIMIT, client_oid=None):
        """Create an order.
        Args:
            action: Action type, `BUY` or `SELL`.
            symbol: Trading pair, e.g. `BTC-USDT`.
            price: Order price.
            quantity: Order quantity.
            order_type: Order type, `MARKET` or `LIMIT`.
            client_oid: Client order id, default is `None`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/spot/v3/orders"
        data = {
            "side": "buy" if action == ORDER_ACTION_BUY else "sell",
            "instrument_id": symbol,
            "margin_trading": 1
        }
        if order_type == ORDER_TYPE_LIMIT:
            data["type"] = "limit"
            data["price"] = price
            data["size"] = quantity
        elif order_type == ORDER_TYPE_MARKET:
            data["type"] = "market"
            if action == ORDER_ACTION_BUY:
                data["notional"] = quantity  # buy price.
            else:
                data["size"] = quantity  # sell quantity.
        else:
            logger.error("order_type error! order_type:", order_type, caller=self)
            return None, "order type error!"
        if client_oid:
            data["client_oid"] = client_oid
        result, error = await self.request("POST", uri, body=data, auth=True)
        return result, error

    async def revoke_order(self, symbol, order_id=None, client_oid=None):
        """Cancelling an unfilled order.
        Args:
            symbol: Trading pair, e.g. `BTC-USDT`.
            order_id: Order id, default is `None`.
            client_oid: Client order id, default is `None`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Notes:
            `order_id` and `order_oid` must exist one, using order_id first.
        """
        if order_id:
            uri = "/api/spot/v3/cancel_orders/{order_id}".format(order_id=order_id)
        elif client_oid:
            uri = "/api/spot/v3/cancel_orders/{client_oid}".format(client_oid=client_oid)
        else:
            return None, "order id error!"
        data = {
            "instrument_id": symbol
        }
        result, error = await self.request("POST", uri, body=data, auth=True)
        if error:
            return order_id, error
        if result["result"]:
            return order_id, None
        return order_id, result

    async def revoke_orders(self, symbol, order_ids=None, client_oids=None):
        """Cancelling multiple open orders with order_id，Maximum 10 orders can be cancelled at a time for each
            trading pair.

        Args:
            symbol: Trading pair, e.g. `BTC-USDT`.
            order_ids: Order id list, default is `None`.
            client_oids: Client order id list, default is `None`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Notes:
            `order_ids` and `order_oids` must exist one, using order_ids first.
        """
        uri = "/api/spot/v3/cancel_batch_orders"
        if order_ids:
            if len(order_ids) > 10:
                logger.warn("only revoke 10 orders per request!", caller=self)
            body = [
                {
                    "instrument_id": symbol,
                    "order_ids": order_ids[:10]
                }
            ]
        elif client_oids:
            if len(client_oids) > 10:
                logger.warn("only revoke 10 orders per request!", caller=self)
            body = [
                {
                    "instrument_id": symbol,
                    "client_oids": client_oids[:10]
                }
            ]
        else:
            return None, "order id list error!"
        result, error = await self.request("POST", uri, body=body, auth=True)
        return result, error

    async def get_open_orders(self, symbol, limit=100):
        """Get order details by order id.

        Args:
            symbol: Trading pair, e.g. `BTC-USDT`.
            limit: order count to return, max is 100, default is 100.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/spot/v3/orders_pending"
        params = {
            "instrument_id": symbol,
            "limit": limit
        }
        result, error = await self.request("GET", uri, params=params, auth=True)
        return result, error

    async def get_order_status(self, symbol, order_id=None, client_oid=None):
        """Get order status.
        Args:
            symbol: Trading pair, e.g. `BTC-USDT`.
            order_id: Order id.
            client_oid: Client order id, default is `None`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Notes:
            `order_id` and `order_oid` must exist one, using order_id first.
        """
        if order_id:
            uri = "/api/spot/v3/orders/{order_id}".format(order_id=order_id)
        elif client_oid:
            uri = "/api/spot/v3/orders/{client_oid}".format(client_oid=client_oid)
        else:
            return None, "order id error!"
        params = {
            "instrument_id": symbol
        }
        result, error = await self.request("GET", uri, params=params, auth=True)
        return result, error

    async def request(self, method, uri, params=None, body=None, headers=None, auth=False):
        """Do HTTP request.

        Args:
            method: HTTP request method. `GET` / `POST` / `DELETE` / `PUT`.
            uri: HTTP request uri.
            params: HTTP query params.
            body: HTTP request body.
            headers: HTTP request headers.
            auth: If this request requires authentication.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        if params:
            query = "&".join(["{}={}".format(k, params[k]) for k in sorted(params.keys())])
            uri += "?" + query
        url = urljoin(self._host, uri)

        if auth:
            timestamp = str(time.time()).split(".")[0] + "." + str(time.time()).split(".")[1][:3]
            if body:
                body = json.dumps(body)
            else:
                body = ""
            message = str(timestamp) + str.upper(method) + uri + str(body)
            mac = hmac.new(bytes(self._secret_key, encoding="utf8"), bytes(message, encoding="utf-8"),
                           digestmod="sha256")
            d = mac.digest()
            sign = base64.b64encode(d)

            if not headers:
                headers = {}
            headers["Content-Type"] = "application/json"
            headers["OK-ACCESS-KEY"] = self._access_key.encode().decode()
            headers["OK-ACCESS-SIGN"] = sign.decode()
            headers["OK-ACCESS-TIMESTAMP"] = str(timestamp)
            headers["OK-ACCESS-PASSPHRASE"] = self._passphrase
        _, success, error = await AsyncHttpRequests.fetch(method, url, body=body, headers=headers, timeout=10)
        return success, error
