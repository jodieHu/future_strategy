from tqsdk import TqApi,TqSim,TqBacktest,BacktestFinished,tafunc
import time
from datetime import date
from tqsdk import *
from tqsdk.tafunc import *
acc=TqSim()


##指标MACD
##DIFF:= EMA(CLOSE,12) - EMA(CLOSE,26);
##DEA:= EMA(DIFF,9);
##DDEA2:=DEA>2;//
##KDEA2:=DEA<2;//

##开仓操作判断
##开多:调取跨周期15分钟指标MACD.DDEA2 和跨周期1小时的 结算价 中的 DSETTLE
##开空:调取跨周期15分钟指标MACD.KDEA2 和跨周期1小时的 结算价 中的 KSETTLE

##风控措施/平仓操作判断
##平多止盈:盈利10%止盈，盘中触发价即时执行止盈
##平空止盈:亏损10%止损，盘中触发价即时执行止损
##平多止损:收盘价<=开多仓以来最高价回落2%，盘中触发价即时执行止损
##平空止损:收盘价>=开空仓以来最低价回升2%，盘中触发价即时执行止损
##平多止损,SP;//盘中触发价止损
##平空止损,BP;//盘中触发价止损

##下单操作
##开多,BPK;//当持有空仓时先100%平空仓后再开1%多仓；无持有多仓时按帐户可用资金1%开多仓。设置为：信号本周期结束前10秒以对手价委托交易
##开空,SPK;//当持有多仓时先100%平多仓后再开1%空仓；无持有空仓时按帐户可用资金1%开空仓。设置为：信号本周期结束前10秒以对手价委托交易
##CLOSEKLINE(2,10);//设置K线提前10秒走完，确认信号下单，K线走完进行复核


currentstate='等待开仓'
type="SHFE.rb2005"
placetime=0
placetimehigh=0
placetimelow=0
cycle=60
f=open("1.txt",'w')

#通过长短周期判断是否开仓
def return_cycle(cycle_context, cycle):
    kline=api.get_kline_serial(type, cycle)
    close=kline['close']
    M20 = tafunc.ma(close, 20)
    M40=tafunc.ma(close, 40)
    DIFF=tafunc.ema(close, 12)-tafunc.ema(close, 26)
    DEA=tafunc.ema(DIFF, 9)
    DDEA2=DEA>2  #结算价上涨
    KDEA2=DEA<2  #结算价下跌
    settle=close
    DSETTLE=settle>=tafunc.ref(settle,1)
    KSETTLE=settle<=tafunc.ref(settle,1)
    dictionary={'M20':M20,'M40':M40,'DIFF':DIFF,'DEA':DEA,'DDEA2':DDEA2,'KDEA2':KDEA2,'DSETTLE':DSETTLE,'KSETTLE':KSETTLE}
    return dictionary[cycle_context]

#通获得多头仓位数据
def get_kline_buy():
    buy=all((tafunc.crossup(return_cycle("M20",60), return_cycle("M40",60)).tolist()[-1], return_cycle("DDEA2",900).tolist()[-1] ,return_cycle("DSETTLE",60*60).tolist()[-1]))
    return buy
#通获得空头仓位数据
def get_kline_put():
    put=all((tafunc.crossup(return_cycle("M40",60), return_cycle("M20",60)).tolist()[-1], return_cycle("KDEA2",900).tolist()[-1] ,return_cycle("KSETTLE",60*60).tolist()[-1]))
    return put

#下单交易指令
def judge_open():
    global currentstate,placetimehigh,placetimelow
    if currentstate=='等待开仓':
        if get_kline_buy():
            api.insert_order(symbol=type, direction="BUY", offset="OPEN", volume=1)
            currentstate='以开多仓等待平仓'
            placetimehigh=api.get_kline_serial(type,cycle)['close'].tolist()[-1]
            f.write("开多仓:"+str(placetimehigh)+'\n')
    if currentstate=='等待开仓':
        if get_kline_put():
            api.insert_order(symbol=type, direction="SELL", offset="OPEN", volume=1)
            currentstate='以开空仓等待平仓'
            placetimelow=api.get_kline_serial(type,cycle)['close'].tolist()[-1]
            f.write("开空仓:"+str(placetimelow)+'\n')

#平所有仓位
def get_cover(type):
    data=api.get_position(type)
    buy1=data['pos_long_his']
    buy2=data['pos_long_today']
    put1=data['pos_short_his']
    put2=data['pos_short_today']
    placetimelow=api.get_kline_serial(type,cycle)['close'].tolist()[-1]
    f.write("平仓价格:"+str(placetimelow)+'\n')
#判断仓位并平仓
    if buy1!=0:
        api.insert_order(symbol=type, direction="SELL", offset="CLOSE", volume=buy1)
    if buy2!=0:
        if type[:4]=="SHFE":
            api.insert_order(symbol=type, direction="SELL", offset="CLOSETODAY", volume=buy2)
        else:
            api.insert_order(symbol=type, direction="SELL", offset="CLOSE", volume=buy2)
    if put1!=0:
        api.insert_order(symbol=type, direction="BUY", offset="CLOSE", volume=put1)
    if put2!=0:
        if type[:4]=="SHFE":
            api.insert_order(symbol=type, direction="BUY", offset="CLOSETODAY", volume=put2)
        else:
            api.insert_order(symbol=type, direction="BUY", offset="CLOSE", volume=put2)

#判断是否要平仓
def cover_test():
    global currentstate,placetimehigh,placetimelow
    currentprice=api.get_kline_serial(type,cycle)['close'].tolist()[-1]
    if currentstate=='以开多仓等待平仓':
        if currentprice>placetimehigh:
            placetimehigh=currentprice
        if currentprice<placetimehigh*0.98:
            get_cover(type)
            currentstate='等待开仓'
            print('平仓条件1')
        buy_position=api.get_position(type)
        if buy_position['float_profit_long']>buy_position["open_cost_long"]*0.1:
            get_cover(type)
            currentstate='等待开仓'
            print("获利平仓")
        if 0-buy_position['float_profit_long']>buy_position["open_cost_long"]*0.1:
            get_cover(type)
            currentstate='等待开仓'
            print("亏损平仓")
    if currentstate=='以开空仓等待平仓':
        if currentprice<placetimelow:
            placetimelow=currentprice
        if currentprice>placetimelow*1.02:
            get_cover(type)
            currentstate='等待开仓'
            print('平仓条件1')
        put_position=api.get_position(type)
        if put_position['float_profit_short']>put_position["open_cost_short"]*0.1:
            get_cover(type)
            currentstate='等待开仓'
            print("获利平仓")
        if 0-put_position['float_profit_short']>put_position["open_cost_short"]*0.1:
            get_cover(type)
            currentstate='等待开仓'
            print("亏损平仓")

#回测
try:
    acc = TqSim()
    api = TqApi(acc, backtest=TqBacktest(start_dt=date(2020, 1, 1), end_dt=date(2020, 4, 1)))
    kline = api.get_kline_serial(type, 60, 300)
    while True:
        api.wait_update()
        print(currentstate)
        judge_open()
        cover_test()
except BacktestFinished as e:
  # 回测结束时会执行这里的代码
  pass
api.close()
f.close()

##1.txt
##开多仓:3333.0
##平仓价格:3402.0
##开空仓:3422.0
##平仓价格:3470.0
##开多仓:3494.0
##平仓价格:3495.0
##开空仓:3462.0
##平仓价格:3440.0
##开空仓:3443.0
##平仓价格:3518.0
##开多仓:3521.0
##平仓价格:3476.0
##开多仓:3489.0
##平仓价格:3439.0
##开空仓:3440.0
##平仓价格:3486.0
##开多仓:3515.0
##平仓价格:3443.0
##开空仓:3414.0
##平仓价格:3325.0
##开多仓:3326.0
