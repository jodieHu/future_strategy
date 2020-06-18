from datetime import date
from tqsdk import TqApi, TqBacktest, TargetPosTask
from sklearn import linear_model
import numpy as np


# 在创建 api 实例时传入 TqBacktest 就会进入回测模式
api = TqApi(backtest=TqBacktest(start_dt=date(2019, 1, 1), end_dt=date(2019, 3, 1)))

#螺纹钢
#热轧卷板

klines_a = api.get_kline_serial( "SHFE.rb1905", 60*60, 100)
klines_b = api.get_kline_serial("SHFE.hc1905", 60*60, 100)
target_pos = TargetPosTask(api, "SHFE.hc1905")

##参看孙阳，2019 “基于协整的商品期货配对交易策略研究”
##取样本内数据价差的四分之一分位数 x，mean 和 sigma 分别表示均值和标准差
##本策略中规定当价差波动超出 mean ± 4. 5sigma 时，进行极端行情下的开仓 操作，此时的止损设置为 mean ± 6. 5sigma。
##当价差由均 值超过阈值时不开仓，当价差向均值回归且达到阈 值时开仓。当价差回归到均值时平仓止盈。


def linear(data1,data2):
    regr = linear_model.LinearRegression()
    data1=np.transpose(np.array(data1)).reshape(1,-1)
    data2=np.transpose(np.array(data2)).reshape(1,-1)
    result=regr.fit(data1,data2)
    alpha = np.mean(result.intercept_)
    beta = np.mean(result.coef_)
    data1_adj = alpha + beta * data2
    residuals = data1_adj - data1
    mean = np.mean(residuals)
    std = np.std(residuals)
    result_all = [mean,std,beta,alpha]    
    return (result_all)

while True:                                                 #判断开仓条件的主循环
    api.wait_update()                                       #等待业务数据更新
    if api.is_changing(klines_b):
        linear_result = linear(klines_a.close_oi,klines_b.close_oi)
        print(linear_result)
        spread = linear_result[3]+linear_result[2]*klines_a['close'].tolist()[-1]-klines_b['close'].tolist()[-1]
        print(spread)
        if spread < linear_result[0]+ 2*linear_result[1]:   #实际调整为2个sigma
            print("此为多头市场")
            target_pos.set_target_volume(50)
        elif spread > linear_result[0]- 2*linear_result[1]:
            print("此为空头市场")
            target_pos.set_target_volume(-50)               #如果触发了，则通过 target_pos 将 目标持仓设置为多头 1 手，具体的调仓工作则由 target_pos 在后台完成
        break                                               #跳出开仓循环，进入下面的平仓循环

while True:                                                 #判断平仓条件的主循环
    api.wait_update()                                       #等待业务数据更新
    if api.is_changing(klines_b):
        linear_result = linear(klines_a.close_oi,klines_b.close_oi)
        spread = linear_result[3]+linear_result[2]*klines_a['close'].tolist()[-1]-klines_b['close'].tolist()[-1]
        if (spread > linear_result[0]+ 7.5*linear_result[1]) or (spread < linear_result[0]< 7.5*linear_result[1]):
            print("止盈")
            target_pos.set_target_volume(0)
        elif (spread < linear_result[0]+4*linear_result[1]) or (spread > linear_result[0]+4*linear_result[1]):
            print("止损")
            target_pos.set_target_volume(0)                 #如果触发了，则通过 target_pos 将 目标持仓设置为多头 1 手，具体的调仓工作则由 target_pos 在后台完成
        break         


api.close()                                                 



##WARNING - 胜率:100.00%,盈亏额比例:inf,收益率:0.17%,年化收益率:23.88%,最大回撤:0.00%,年化夏普率:13.9668
