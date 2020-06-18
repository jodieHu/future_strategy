##需要下载的包：tqsdk，numpy，datetime，sklearn
##需要配置的环境：pycharm/vscode

from datetime import date
from tqsdk import TqApi, TqBacktest, TargetPosTask
import numpy as pd

# 使用实盘帐号直连行情和交易服务器
# from tqsdk import TqApi, TqAccount
# api = TqApi(TqAccount("H海通期货", "022631", "123456"))
# 使用模拟帐号直连行情服务器
# from tqsdk import TqApi, TqSim
# api = TqApi(TqSim())  # 不填写参数则默认为 TqSim() 模拟账号


# 在创建 api 实例时传入 TqBacktest 就会进入回测模式
api = TqApi(backtest=TqBacktest(start_dt=date(2019, 2, 1), end_dt=date(2019, 3, 1)))

##相对强弱指标(RSI)由 Wels Wilder于1978年在他的《技术交易系统新思路》一书中提出
##用于某段时间内价格的变化状况预测价格的变化方位，并按照价格的涨跌幅度判别市场的强弱
##RSI的计算办法为:RSI参数普遍用交易日天数有5、9、14日。
##市场强势时占比大，市场弱势时占比小，RSI能够运用有差别的天数参数 。
##参数小的为短时 RSI，参数大的为长时 RSI，短时 RSI大于长时 RSI为多头市场，短时 RSI小于长时 RSI为空头市场。
##短时 RSI1由下向上穿过长时 RSI2时，此时为买入信号，做多;短时 RSI1由上向下穿过长时 RSI2时，此时为卖出信号，做空。


klines_long = api.get_kline_serial("SHFE.rb1905", 24 * 60 * 60, data_length=9)
klines_short = api.get_kline_serial("SHFE.rb1905", 24 * 60 * 60, data_length=5)
#print(klines_short.close_oi)
# 创建 m1901 的目标持仓 task，该 task 负责调整 m1901 的仓位到指定的目标仓位
target_pos = TargetPosTask(api, "SHFE.rb1905")

print("策略开始运行")

##建立RSI指标
def RSI(data):
  dif_close=data.diff(periods=1)
  down=0
  up=0
  for item in dif_close:
      if item != item:
          continue
     # print(item)
      #print(type(item))
      if item <0:
          down = down+item
      else:
          up = up+item
  # print(down)
  # print(up)
  rsi=up/(up+down)
  return rsi

while True:                                                 #判断开仓/平仓条件的主循环
  api.wait_update()                                         #等待业务数据更新
  if api.is_changing(klines_short):

      rsi_short = RSI(klines_short.close_oi)
      rsi_long = RSI(klines_long.close_oi)
      #print(rsi_short,rsi_long)
      if rsi_short < rsi_long:
          print("此为多头市场")
          target_pos.set_target_volume(50)                   #如果触发了，则通过 target_pos 将目标持仓设置为多头 1 手，具体的调仓工作则由 target_pos 在后台完成
      elif rsi_short > rsi_long:
          print("此为空头市场")
          target_pos.set_target_volume(-50)     
      #break                                               #跳出开仓循环
api.close()


##WARNING - 胜率:75.00%,盈亏额比例:7.43,收益率:0.58%,年化收益率:9.52%,最大回撤:0.76%,年化夏普率:1.7782
