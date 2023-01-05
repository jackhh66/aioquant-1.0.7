# -*- coding:utf-8 -*-

"""
Huobi Trade module.
https://huobiapi.github.io/docs/spot/v1/cn

Author: HuangTao
Date:   2018/08/30
Email:  huangtao@ifclover.com
"""

import base64
import datetime
import hashlib
import hmac
import json
import urllib
from urllib import parse
from urllib.parse import urljoin

from aioquant.utils.web import AsyncHttpRequests

__all__ = ("HuobiRestAPI", )


class HuobiRestAPI:
    """Huobi REST API client.

    Attributes:
        access_key: Account's ACCESS KEY.
        secret_key: Account's SECRET KEY.
        host: HTTP request host, default `https://api.huobi.pro`.
    """

    def __init__(self, access_key, secret_key, host=None):
        """Initialize REST API client."""
        self._host = host or "https://api.huobi.pro"
        self._access_key = access_key
        self._secret_key = secret_key
        self._account_id = None

    async def get_server_time(self):
        """This endpoint returns the current system time in milliseconds adjusted to Singapore time zone.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/v1/common/timestamp"
        success, error = await self.request("GET", uri)
        return success, error

    async def get_exchange_info(self):
        """Get exchange information.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/v1/common/symbols"
        success, error = await self.request("GET", uri)
        return success, error

    async def get_orderbook(self, symbol, depth=20, step="step0"):
        """Get latest orderbook information.

        Args:
            symbol: Symbol name, e.g. `ethusdt`.
            depth: The number of market depth to return on each side, `5` / `10` / `20`, default is 10.
            step: Market depth aggregation level, `step0` / `step1` / `step2` / `step3` / `step4` / `step5`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Note:
            When type is set to `step0`, the default value of `depth` is 150 instead of 20.
        """
        uri = "/market/depth"
        params = {
            "symbol": symbol,
            "depth": depth,
            "type": step
        }
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_trade(self, symbol):
        """Get latest trade information.

        Args:
            symbol: Symbol name, e.g. `ethusdt`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/market/trade"
        params = {
            "symbol": symbol
        }
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_kline(self, symbol, interval="1min", limit=150):
        """Get kline information.

        Args:
            symbol: Symbol name, e.g. `ethusdt`.
            interval: Kline interval type, `1min` / `5min` / `15min` / `30min` / `60min` / `4hour` / `1day` / `1mon` / `1week` / `1year`.
            limit: Number of results per request. (default 150, max 2000.)

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Notes:
            If start and end are not sent, the most recent klines are returned.
        """
        uri = "/market/history/kline"
        params = {
            "symbol": symbol,
            "period": interval,
            "size": limit
        }
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_user_accounts(self):
        """This endpoint returns a list of accounts owned by this API user.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/v1/account/accounts"
        success, error = await self.request("GET", uri, auth=True)
        return success, error

    async def _get_account_id(self):
        if self._account_id:
            return self._account_id
        success, error = await self.get_user_accounts()
        if error:
            return None
        for item in success["data"]:
            if item["type"] == "spot":
                self._account_id = item["id"]
                return self._account_id
        return None

    async def get_account_balance(self):
        """This endpoint returns the balance of an account specified by account id.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        account_id = await self._get_account_id()
        uri = "/v1/account/accounts/{account_id}/balance".format(account_id=account_id)
        success, error = await self.request("GET", uri, auth=True)
        return success, error

    async def get_balance_all(self):
        """This endpoint returns the balances of all the sub-account aggregated.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/v1/subuser/aggregate-balance"
        success, error = await self.request("GET", uri, auth=True)
        return success, error

    async def create_order(self, symbol, price, quantity, order_type, client_order_id=None):
        """Create an order.
        Args:
            symbol: Symbol name, e.g. `ethusdt`.
            price: Price of each contract.
            quantity: The buying or selling quantity.
            order_type: Order type, `buy-market` / `sell-market` / `buy-limit` / `sell-limit`.
            client_order_id: Client order id.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/v1/order/orders/place"
        account_id = await self._get_account_id()
        info = {
            "account-id": account_id,
            "price": price,
            "amount": quantity,
            "source": "api",
            "symbol": symbol,
            "type": order_type
        }
        if order_type == "buy-limit" or order_type == "sell-limit":
            info["price"] = price
        if client_order_id:
            info["client-order-id"] = client_order_id
        success, error = await self.request("POST", uri, body=info, auth=True)
        return success, error

    async def revoke_order(self, order_id):
        """Cancelling an unfilled order.
        Args:
            order_id: Order id.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/v1/order/orders/{order_id}/submitcancel".format(order_id=order_id)
        success, error = await self.request("POST", uri, auth=True)
        return success, error

    async def revoke_orders(self, order_ids):
        """Cancelling unfilled orders.
        Args:
            order_ids: Order id list.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/v1/order/orders/batchcancel"
        body = {
            "order-ids": order_ids
        }
        success, error = await self.request("POST", uri, body=body, auth=True)
        return success, error

    async def get_open_orders(self, symbol, limit=500):
        """Get all open order information.

        Args:
            symbol: Symbol name, e.g. `ethusdt`.
            limit: The number of orders to return, [1, 500].

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/v1/order/openOrders"
        account_id = await self._get_account_id()
        params = {
            "account-id": account_id,
            "symbol": symbol,
            "size": limit
        }
        success, error = await self.request("GET", uri, params=params, auth=True)
        return success, error

    async def get_order_status(self, order_id):
        """Get order details by order id.

        Args:
            order_id: Order id.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/v1/order/orders/{order_id}".format(order_id=order_id)
        success, error = await self.request("GET", uri, auth=True)
        return success, error

    async def request(self, method, uri, params=None, body=None, auth=False):
        """Do HTTP request.

        Args:
            method: HTTP request method. `GET` / `POST` / `DELETE` / `PUT`.
            uri: HTTP request uri.
            params: HTTP query params.
            body:   HTTP request body.
            auth: If this request requires authentication.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        url = urljoin(self._host, uri)
        if auth:
            timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            params = params if params else {}
            params.update({"AccessKeyId": self._access_key,
                           "SignatureMethod": "HmacSHA256",
                           "SignatureVersion": "2",
                           "Timestamp": timestamp})

            host_name = urllib.parse.urlparse(self._host).hostname.lower()
            params["Signature"] = self.generate_signature(method, params, host_name, uri)

        if method == "GET":
            headers = {
                "Content-type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/39.0.2171.71 Safari/537.36"
            }
        else:
            headers = {
                "Accept": "application/json",
                "Content-type": "application/json"
            }
        _, success, error = await AsyncHttpRequests.fetch(method, url, params=params, data=body, headers=headers,
                                                          timeout=10)
        if error:
            return success, error
        if not isinstance(success, dict):
            success = json.loads(success)
        if success.get("status") != "ok":
            return None, success
        return success, None

    def generate_signature(self, method, params, host_url, request_path):
        query = "&".join(["{}={}".format(k, parse.quote(str(params[k]))) for k in sorted(params.keys())])
        payload = [method, host_url, request_path, query]
        payload = "\n".join(payload)
        payload = payload.encode(encoding="utf8")
        secret_key = self._secret_key.encode(encoding="utf8")
        digest = hmac.new(secret_key, payload, digestmod=hashlib.sha256).digest()
        signature = base64.b64encode(digest)
        signature = signature.decode()
        return signature
