"""
Stock Market
Cinyoung Hur, cinyoung.hur@gmail.com
James Park, laplacian.k@gmail.com
seoulai.com
2018
"""
import copy
from typing import Dict
from typing import List
from typing import Tuple

import pygame
from pygame.locals import QUIT
import numpy as np

from seoulai_gym.envs.market.base import Constants
from seoulai_gym.envs.market.price import Price, Exchange 
from seoulai_gym.envs.market.graphics import Graphics


class Market():
    def __init__(
        self,
        state: str=None,
    ) -> None:
        """Initialize market and its visualization.
        Args:
            state: Optional, path to saved game state. TODO
        Returns:
            None
        """
        # self.state_size = 10
        self.action_size = 3    # buy, sell, hold
        self.traders = 0    # for multi-players
        self.init()

        # graphics is for visualization
        self.graphics = Graphics()
        self.pause = False  # pause game

    def init(
        self,
    ):
        self.t = 0
        self.max_t_size = 100 

    def select(
        self,
        exchange: Exchange
    ) -> None:
        self.price = Price(exchange)

    def reset(
        self
    ) -> List:
        """Reset all variables and initialize new game.
        Returns:
            obs: Information about trading parameters.
        """

        self.init()

        df = self.price.price_ext[:1]
 
        obs = dict(data=df,
                   fee_rt=self.price.exchange.fee_rt,
                   cur_price=df.Close.ix[0],
                   t = self.t)
        return obs

    def step(
        self,
        agent,
        decision,
        trad_price: float,
        trad_qty: float,
    ):
        """Make a step (= move) within market.
        Args:
            agent: Agent making a decision(buy, sell and hold).
            decision : buy, sell or hold. Agent position.
            trad_price: Price that Agent want to trade.
            trad_qty: Quantity that Agent want to trade.
        Returns:
            obs: Information of price history and fee ratio.
            rew: Reward for perfomed step.
            done: Information about end of game.
            info: Additional information about current step.
        """

        next_obs, rew, done, info = self.conclude(
            agent, decision, trad_price, trad_qty)

        return copy.deepcopy(next_obs), rew, done, info

    def conclude(
        self,
        agent,
        decision,
        trad_price: float,
        trad_qty: float,
    )-> Tuple[float, int, bool, Dict]:
        # TODO : reward can be changed. ex. daily return, duration of winning.
        rew = 0
        done = False

        info = {}

        # It is assumed that order is concluded as agent action.
        # in real world, it can't be possible.
        # TODO : develop backtesting logic like real world. ex. slippage
        # TODO : crypto currency tax doesn't exist now.
        ccld_price = trad_price    # concluded price. (체결가격)
        ccld_qty = trad_qty   # concluded quantity. (체결수량)

        # total amount of moved money. (거래금액)
        trading_amt = ccld_price*ccld_qty
        fee = trading_amt*self.price.exchange.fee_rt    # fee(commission, 수수료)

        # previus potfolio value(previous cash+asset_value), 이전 포트폴리오 가치(이전 현금 + 이전 자산 가치)
        priv_pflo_value = agent.cash+agent.asset_val

        if decision == Constants.BUY:
            # after buying, cash will decrease. (매수 후, 현금은 줄어든다.)
            agent.cash = agent.cash-trading_amt-fee
            # quantity of asset will increase. (매수 후, 자산 수량은 늘어난다.)
            agent.asset_qty = agent.asset_qty + ccld_qty
        elif decision == Constants.SELL:
            # after selling, cash will increase. (매도 후, 현금은 증가한다.)
            agent.cash = agent.cash+(trading_amt-fee)
            # quantity of asset will decrease. (매도 후, 자산 수량은 줄어든다.)
            agent.asset_qty = agent.asset_qty - ccld_qty

        cur_price = self.price.price_list[self.t]    # current price (현재가)
        # current asset value is asset_qty x current price (현재 자산 가치 = 자산 수량 x 현재가)
        agent.asset_val = agent.asset_qty*cur_price
        # current potfolio value(current cash+asset_value) 현재 포트폴리오 가치(현재 현금, 현재 자산 가치)
        cur_pflo_value = agent.cash+agent.asset_val

        # money that you earn or lose in 1 t. (1 t 동안의 decision으로 변화한 포트폴리오 가치를 reward로 잡음)
        rew = 10.0*np.sign(((cur_pflo_value/priv_pflo_value)-1)*100)
        rew = -1.0 if decision == Constants.HOLD else rew

        # vaildation
        # TODO: self.stock_total_volume will be discussed.
        """
        if decision == Constants.BUY and (self.stock_total_volume - stock_volume) > 0:
            self.stock_total_volume = self.stock_total_volume - stock_volume
        elif decision == Constants.SELL:
            self.stock_total_volume = self.stock_total_volume + stock_volume
        """

        """
        if self.stock_total_volume == 0:
            done = True
        else:
            done = False
        """

        # end of trading game?
        msg = ""
        if self.t >= self.max_t_size-1:
            done = True
            msg = "t overflow!! max_t_size : %d, current_t : %d " % (
                self.max_t_size, self.t)

        total_return = ((cur_pflo_value/agent.init_cash)-1)*100

        # comparing with buy and hold algo
        # if agent.invested:
        #    next_price = self.price.price_list[self.t+1]
        #    print(next_price)
        #    print(agent.bah_base)
        #    bah_return = ((next_price/agent.bah_base)-1)*100
        #    print("%lf vs %lf"%(total_return, bah_return))
        #    if total_return < bah_return:
        #        done = True
        #        msg = "your algo is worse than buy and hold algo!!!"

        # bankrupt
        if cur_pflo_value <= 0:
            done = True
            msg = "you bankrupt!!!"

        # next t
        nt = self.t + 1
        self.t = nt
        next_ts = self.price.price_ext[:nt+1]
        next_cur_price = next_ts.Close.ix[-1]
        # we should offer raw data. then, users can customize their algo easily.
        obs = dict(data=next_ts,
                   fee_rt=self.price.exchange.fee_rt,
                   cur_price=next_cur_price,
                   t=nt)

        info["priv_pflo_value"] = priv_pflo_value
        info["cur_pflo_value"] = cur_pflo_value
        info["1t_return"] = cur_pflo_value-priv_pflo_value
        info["1t_ret_ratio"] = ((cur_pflo_value/priv_pflo_value)-1)*100
        info["fee"] = fee
        info["portfolio_value"] = cur_pflo_value
        info["msg"] = msg

        return obs, rew, done, info

    def render(
        self,
        agent,
        info,
        decision,
    ) -> None:
        """Display current state of board.
        Returns:
            None
        """
        self.graphics.update(
            self.price.price_list[:self.t+1],
            agent,
            info,
            decision
        )
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.pause = True
                    self.paused()
                if event.key == pygame.K_c:
                    self.pause = False

    def paused(self):

        while self.pause:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_c:
                        self.pause = False

            pygame.display.update()

    def close(
        self,
    ) -> None:
        pygame.display.quit()
        pygame.font.quit()
        pygame.quit()
        # pygame has to be again initialized, otherwise window does not close
        pygame.init()
