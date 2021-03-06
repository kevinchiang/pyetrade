from enum import Enum

import requests

from ._auth import auth
from ._decorators import ProcessResult
from ._urls import order_urls
from ._responses import order_response
from ._error import EtradeError
import uuid

__author__ = 'glenn'


class EnumOrderTerm(Enum):
    GOOD_UNTIL_CANCEL = 'GOOD_UNTIL_CANCEL'
    GOOD_FOR_DAY = 'GOOD_FOR_DAY'
    IMMEDIATE_OR_CANCEL = 'IMMEDIATE_OR_CANCEL'
    FILL_OR_KILL = 'FILL_OR_KILL'


class EnumEquityOrderAction(Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    BUY_TO_COVER = 'BUY_TO_COVER'
    SELL_SHORT = 'SELL_SHORT'


class EnumOptionOrderAction(Enum):
    BUY_OPEN = 'BUY_OPEN'
    SELL_OPEN = 'SELL_OPEN'
    BUY_CLOSE = 'BUY_CLOSE'
    SELL_CLOSE = 'SELL_CLOSE'


class EnumOptionPriceType(Enum):
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    STOP = 'STOP'
    STOP_LIMIT = 'STOP_LIMIT'


class EnumEquityPriceType(Enum):
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    STOP = 'STOP'
    STOP_LIMIT = 'STOP_LIMIT'
    MARKET_ON_CLOSE = 'MARKET_ON_CLOSE'


class EnumRoutingDestination(Enum):
    AUTO = 'AUTO'
    ARCA = 'ARCA'
    NSDQ = 'NSDQ'
    NYSE = 'NYSE'


class EnumMarketSession(Enum):
    REGULAR = 'REGULAR'
    EXTENDED = 'EXTENDED'


class EnumCallOrPut(Enum):
    CALL = 'CALL'
    PUT = "PUT"


#
# def order_factory(account_id=None, quantity=None, order_term=None, price_type=None,
#                   limit_price=None, all_or_none=None, reserve_order=None, reserve_quantity=None):
#
#     """
#
#
#     :param account_id: account id
#     :type account_id: int
#     :param quantity: quantity
#     :type quantity: int
#     :param order_term: order term
#     :type order_term: EnumOrderTerm
#     :param price_type: price type
#     :type price_type: EnumEquityPriceType
#     :param stop_price: stop price
#     :type stop_price: float|int|None
#     :param limit_price: limit price
#     :param all_or_none: float|int|None
#     :param reserve_order: is reserve order
#     :type reserve_order: bool
#     :param reserve_quantity: is reserve quantity
#     :type reserve_quantity: bool
#     :raise Exception:
#     """
#
# pass


class _OrderPropsBase(object):
    def __init__(self, account_id, quantity, order_term, price_type, stop_price, limit_price,
                 all_or_none, reserve_order, reserve_quantity):
        """


        :param account_id: account id
        :type account_id: int
        :param quantity: quantity
        :type quantity: int
        :param order_term: order term
        :type order_term: EnumOrderTerm
        :param price_type: price type
        :type price_type: EnumEquityPriceType
        :param stop_price: stop price
        :type stop_price: float|int|None
        :param limit_price: limit price
        :param all_or_none: float|int|None
        :param reserve_order: is reserve order
        :type reserve_order: bool
        :param reserve_quantity: is reserve quantity
        :type reserve_quantity: bool
        :raise Exception:
        """
        assert isinstance(account_id, int)
        assert isinstance(quantity, int)
        assert isinstance(order_term, EnumOrderTerm)
        assert isinstance(price_type, EnumEquityPriceType)
        assert isinstance(stop_price, (float, type(None),))
        assert isinstance(limit_price, (float, type(None),))
        assert isinstance(all_or_none, bool)
        assert isinstance(reserve_order, bool)

        self.accountId = account_id
        self.quantity = quantity

        self.priceType = price_type.value

        # Need stop price if in these values
        if price_type in (EnumEquityPriceType.STOP, EnumEquityPriceType.STOP_LIMIT) \
                and stop_price is None:
            raise Exception('need to add a stop price for these price types')
        self.stopPrice = stop_price

        # Need limit price if in these values
        if price_type in (EnumEquityPriceType.LIMIT, EnumEquityPriceType.STOP_LIMIT) \
                and limit_price is None:
            raise Exception('need to add a limit price for these price types')
        self.limitPrice = limit_price

        self.reserveOrder = reserve_order
        if reserve_order and reserve_quantity is None:
            raise Exception('need reserve quantity')
        self.reserveQuantity = reserve_quantity

        self.orderTerm = order_term.value
        self.allOrNone = all_or_none

        if self.allOrNone:
            if price_type not in [EnumEquityPriceType.LIMIT, EnumEquityPriceType.STOP_LIMIT]:
                raise Exception('only limit or stop limit with all or none')
            if quantity < 300:
                raise Exception('quantity of 300 or more with all or none')

        self.clientOrderId = str(uuid.uuid1()).upper().replace('-', '')[:20]
        self.previewId = None

        if order_term in [EnumOrderTerm.IMMEDIATE_OR_CANCEL, EnumOrderTerm.FILL_OR_KILL] \
                and price_type not in [EnumEquityPriceType.LIMIT, EnumEquityPriceType.STOP_LIMIT]:
            raise Exception('only limit orders with order term immediate_or_cancel or fill_or_kill')

    @property
    def prop_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}


class EquityOrderProps(_OrderPropsBase):
    def __init__(
            self,
            account_id,
            quantity,
            symbol,
            order_action,
            all_or_none=False,
            order_term=EnumOrderTerm.GOOD_FOR_DAY,
            market_session=EnumMarketSession.REGULAR,
            price_type=EnumEquityPriceType.MARKET,
            routing_destination=EnumRoutingDestination.AUTO,
            stop_price=None,
            limit_price=None,
            reserve_order=False,
            reserve_quantity=None,
            preview_id=None
    ):
        """
        Equity order properties

        :param account_id: account id
        :type account_id: int
        :param quantity: quantity
        :type quantity: int
        :param symbol: symbol
        :type symbol: str
        :param order_action: order action
        :type order_action: EnumEquityOrderAction
        :param market_session: market session
        :type market_session: EnumMarketSession
        :param routing_destination: routing destination
        :type routing_destination: EnumRoutingDestination
        :return:
        """

        assert isinstance(account_id, int)
        assert isinstance(quantity, int)
        assert isinstance(symbol, str)
        assert isinstance(order_action, EnumEquityOrderAction)
        assert isinstance(market_session, EnumMarketSession)
        assert isinstance(routing_destination, EnumRoutingDestination)

        pass_args = dict(account_id=account_id, quantity=quantity, order_term=order_term,
                         price_type=price_type, stop_price=stop_price, limit_price=limit_price,
                         all_or_none=all_or_none, reserve_order=reserve_order, reserve_quantity=reserve_quantity)

        super().__init__(**pass_args)
        self.symbol = symbol.upper()
        self.orderAction = order_action.value
        self.marketSession = market_session.value
        self.routingDestination = routing_destination.value
        self.previewId = preview_id


class EquityOrderChangeProps(_OrderPropsBase):
    def __init__(self, account_id, quantity, order_num,
                 all_or_none=False,
                 order_term=EnumOrderTerm.GOOD_FOR_DAY,
                 price_type=EnumEquityPriceType.MARKET,
                 stop_price=None,
                 limit_price=None,
                 reserve_order=False,
                 reserve_quantity=None,
                 preview_id=None):
        """
        Equity order change properties

        :param account_id: account id
        :type account_id: int
        :param quantity: quantity
        :type quantity: int
        :param order_num: order number
        :type order_num: int
        :return:
        """
        assert isinstance(account_id, int)
        assert isinstance(quantity, int)
        assert isinstance(order_num, int)

        pass_args = dict(account_id=account_id, quantity=quantity, order_term=order_term,
                         price_type=price_type, stop_price=stop_price, limit_price=limit_price,
                         all_or_none=all_or_none, reserve_order=reserve_order, reserve_quantity=reserve_quantity)

        super().__init__(**pass_args)
        self.orderNum = order_num
        self.previewId = preview_id


class OptionOrderProps(_OrderPropsBase):
    def __init__(
            self,
            account_id,
            quantity,
            symbol,
            order_action,
            stop_limit_price,
            call_or_put,
            strike_price,
            expiration_year,
            expiration_month,
            expiration_day,
            market_session=EnumMarketSession.REGULAR,
            routing_destination=EnumRoutingDestination.AUTO,
            **kwargs):
        """
        Option order properties

        :param account_id: account id
        :type account_id: int
        :param quantity: quantity
        :type quantity: int order_enums
        :param symbol: symbol
        :type symbol: str
        :param order_action: order action
        :type order_action: EnumOptionOrderAction
        :param stop_limit_price: stop limit price
        :type stop_limit_price: int|float
        :param call_or_put: call or put
        :type call_or_put: EnumCallOrPut
        :param strike_price: strike price
        :type strike_price: int|float
        :param expiration_year: expiration year
        :type expiration_year: int
        :param expiration_month: expiration month
        :type expiration_month: int
        :param expiration_day: expiration day
        :type expiration_day: int
        :param market_session: market session
        :type market_session: EnumMarketSession
        :param routing_destination: routing destination
        :type routing_destination: EnumRoutingDestination
        :param kwargs: kwargs
        :type kwargs: dict
        :return:
        """
        assert isinstance(call_or_put, EnumCallOrPut)
        assert isinstance(symbol, str)
        assert isinstance(order_action, EnumOptionOrderAction)
        assert isinstance(strike_price, (float, int,))
        assert isinstance(stop_limit_price, (float, int,))
        assert isinstance(expiration_year, int)
        assert isinstance(expiration_month, int)
        assert isinstance(expiration_day, int)
        assert isinstance(market_session, EnumMarketSession)
        assert isinstance(routing_destination, EnumRoutingDestination)
        super().__init__(account_id, quantity, **kwargs)
        self.orderAction = order_action.value
        self.marketSession = market_session.value
        self.stopLimitPrice = stop_limit_price
        self.symbolInfo = dict({
            'symbol': symbol.upper(),
            'callOrPut': call_or_put.value,
            'strikePrice': strike_price,
            'expirationYear': expiration_year,
            'expirationMonth': expiration_month,
            'expirationDay': expiration_day
        })


class OptionOrderChangeProps(_OrderPropsBase):
    def __init__(self, account_id, quantity, order_num, stop_limit_price=None, **kwargs):
        """
        Option order change properties

        :param account_id: account id
        :type account_id: int
        :param quantity: quantity
        :type quantity: int
        :param order_num: order number
        :type order_num: int
        :param stop_limit_price: stop limit price
        :type stop_limit_price: int|float
        :param kwargs: kwargs
        :type kwargs: dict
        :return:
        """
        assert isinstance(account_id, int)
        assert isinstance(quantity, int)
        assert isinstance(order_num, int)
        assert isinstance(stop_limit_price, (float, int, type(None)))
        super().__init__(account_id, quantity, **kwargs)
        self.orderNum = order_num
        self.stopLimitPrice = stop_limit_price


@ProcessResult(order_response.OrderListResponse)
def list_orders(account_id):
    """
    list orders

    :param account_id: account id
    :type account_id: int
    :return: the order list response
    :rtype: order_response.OrderListResponse|EtradeError
    """
    assert isinstance(account_id, int)
    return requests.get(order_urls.orders_list(account_id), auth=auth.get_current)


@ProcessResult(order_response.OrderCancelResponse)
def cancel_order(account_id, order_id):
    """
    Cancel order

    :param account_id: account id
    :type account_id: int
    :param order_id: order id
    :type order_id: int
    :return: the cancel response
    :rtype: order_response.OrderCancelResponse|EtradeError
    """
    data = {
        "cancelOrder": {
            "-xmlns": "http://order.etws.etrade.com",
            "cancelOrderRequest": {
                "accountId": account_id,
                "orderNum": order_id
            }
        }
    }

    return requests.post(order_urls.orders_cancel(), json=data, auth=auth.get_current)


#
@ProcessResult(order_response.EquityOrderPreview)
def equity_order_preview(equity_order_props):
    """
    Preview equity order

    :param equity_order_props: the equity order properties
    :type equity_order_props: EquityOrderProps
    :return: equity preview response
    :rtype: order_response.EquityOrderPreview|EtradeError
    """
    assert isinstance(equity_order_props, EquityOrderProps)

    data = {
        "PreviewEquityOrder": {
            # "-xmlns": "http://order.etws.etrade.com",
            "EquityOrderRequest": equity_order_props.prop_dict
        }
    }

    return requests.post(order_urls.orders_equity_preview(), json=data, auth=auth.get_current)


@ProcessResult(order_response.EquityOrderPlace)
def equity_order_place(equity_order_props):
    """
    Place Equity Order

    :param equity_order_props: equity order properties
    :type equity_order_props: EquityOrderProps
    :return: place order response
    :rtype: order_response.EquityOrderPlace|EtradeError
    """
    assert isinstance(equity_order_props, EquityOrderProps)

    data = {
        "PlaceEquityOrder": {
            # "-xmlns": "http://order.etws.etrade.com",
            "EquityOrderRequest": equity_order_props.prop_dict
        }
    }
    return requests.post(order_urls.orders_equity_place(), json=data, auth=auth.get_current)


@ProcessResult(order_response.EquityOrderChangePreview)
def equity_change_preview(equity_order_change_props):
    """
    Change equity order preview

    :param equity_order_change_props: change equity order properties
    :type equity_order_change_props: EquityOrderChangeProps
    :return: the change preview response
    :rtype: order_response.EquityOrderChangePreview|EtradeError
    """

    assert isinstance(equity_order_change_props, EquityOrderChangeProps)

    data = {
        "previewChangeEquityOrder": {
            # "-xmlns": "http://order.etws.etrade.com",
            "changeEquityOrderRequest": equity_order_change_props.prop_dict
        }
    }

    return requests.post(order_urls.orders_equity_change_preview(), json=data, auth=auth.get_current)


@ProcessResult(order_response.EquityOrderChangePlace)
def equity_change_place(equity_order_change_props):
    """
    Place equity order change

    :param equity_order_change_props:
    :type equity_order_change_props: EquityOrderChangeProps
    :return: the change response
    :rtype: order_response.EquityOrderChangePlace|EtradeError
    """
    assert isinstance(equity_order_change_props, EquityOrderChangeProps)
    data = {
        "placeChangeEquityOrder": {
            "-xmlns": "http://order.etws.etrade.com",
            "changeEquityOrderRequest": equity_order_change_props.prop_dict
        }
    }

    return requests.post(order_urls.orders_equity_change_place(), json=data, auth=auth.get_current)

#
# @ProcessResult('previewOptionOrderResponse', add_preview_id=True)
# def option_order_preview(option_order_props):
#     """
#     Preview option order
#
#     :param option_order_props: the option order properties
#     :type option_order_props: OptionOrderProps
#     :return: the option order preview response
#     :rtype: Response
#     """
#     assert isinstance(option_order_props, OptionOrderProps)
#
#     data = {
#         "PreviewOptionOrder": {
#             "-xmlns": "http://order.etws.etrade.com",
#             "OptionOrderRequest": option_order_props.get_prop_dict()
#         }
#     }
#
#     return requests.post(order_urls.orders_option_preview, json=data, auth=auth.current)
#
#
# @ProcessResult('placeOptionOrderResponse')
# def option_order_place(option_order_props):
#     """
#     Place option order
#
#     :param option_order_props: the option order properties
#     :type option_order_props: OptionOrderProps
#     :return: the option order place response
#     :rtype: Response
#     """
#     assert isinstance(option_order_props, OptionOrderProps)
#
#     data = {
#         "PlaceOptionOrder": {
#             "-xmlns": "http://order.etws.etrade.com",
#             "OptionOrderRequest": option_order_props.get_prop_dict()
#         }
#     }
#
#     return requests.post(order_urls.orders_option_place, json=data, auth=auth.current)
#
#
# @ProcessResult('previewChangeOptionOrderResponse', add_preview_id=True)
# def option_change_preview(option_change_props):
#     """
#     Option order change preview
#
#     :param option_change_props: the option order change properties
#     :type option_change_props: OptionOrderChangeProps
#     :return: the option order change preview response
#     :rtype: Response
#     """
#     assert isinstance(option_change_props, OptionOrderChangeProps)
#     data = {
#         "previewChangeOptionOrder": {
#             "-xmlns": "http://order.etws.etrade.com",
#             "changeOptionOrderRequest": option_change_props.get_prop_dict()
#         }
#     }
#
#     return requests.post(order_urls.orders_option_change_preview, json=data, auth=auth.current)
#
#
# @ProcessResult('placeChangeOptionOrderResponse')
# def option_change_place(option_change_props):
#     """
#     Option order change place
#
#     :param option_change_props: the option order change properties
#     :type option_change_props: OptionOrderChangeProps
#     :return: the option order change place response
#     :rtype: Response
#     """
#     assert isinstance(option_change_props, OptionOrderChangeProps)
#
#     data = {
#         "placeChangeOptionOrder": {
#             "-xmlns": "http://order.etws.etrade.com",
#             "changeOptionOrderRequest": option_change_props.get_prop_dict()
#         }
#     }
#
#     return requests.post(order_urls.orders_option_change_place, json=data, auth=auth.current)
