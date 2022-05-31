'''
使用 CPU 暴力搜索 D.C.4 ダ・カーポ 4 游戲的激活碼的程序。

Author: 冬夜 @esuOneGov, esuOneGov@galgamer.eu.org

本程序工作原理：
直接窮舉 11 位的序列號肯定是不現實的，所以使用無頭蒼蠅碰運氣法來尋找激活碼

我逆向了 DC4 的激活碼校驗函數，并且把實現原理重新用 Python 表現，
程序在運行時會隨機生成各種字符串，然後經過判定，如果有效，則 print 出來。

運行這個程序需要 1.5G 的 RAM 空間，平均一分鐘可以搜出兩個有效激活碼
'''
import random, time, itertools, multiprocessing


# ------------------------------------------------------
# 校驗一個激活碼是否有效，能否通過 stage1 和 stage2，如果有效則 print 出來
# serial: 待檢測的激活碼
# data_calc_a_value4: 提前計算好的 44D390（計算一個值）的結果表，填入四位字符串后能直接查出結果
# data_strange_op8: eax 經過八次奇怪的操作之後得到的值，也提前計算好以便查表了
# 返回值：沒有
# ------------------------------------------------------
def calc(serial, __, data_calc_a_value4, _, data_strange_op8):
    moved_serial = change_order(serial)

    # print(moved_serial)
    result3 = data_calc_a_value4[moved_serial[7:11]]  # calc_a_value(moved_serial[7:11], 4)
    # print(hex(result3))
    result4 = sub_44D2A0(moved_serial, 7, data_strange_op8)
    # print(hex(result4))

    # 44d4e8
    multiple = result4 * 0x51eb851f
    # eax = multiple & 0xffffffff
    edx = ((multiple >> 32) & 0xffffffff) >> 3
    eax = edx + (edx >> 31)
    edx = result4 - eax
    edx = (edx * 0x19) & 0xffffffff
    edx += result4
    # print(hex(edx))

    if edx != result3:
        return
    else:
        # (f'stage 1 success {serial}')
        pass

    # stage 2 44D519

    result2 = calc_a_value(moved_serial[2:7], 5)  # esi
    # print(result2)
    multiple = result2 * 0x6B5FCA6B
    edx = ((multiple >> 32) & 0xffffffff) >> 0x16
    eax = edx + (edx >> 31)
    eax = (eax * 0x989680) & 0xffffffff
    ecx = result2 - eax
    # print(hex(ecx))

    multiple = 0x2aaaaaab * ecx
    edx = ((multiple >> 32) & 0xffffffff)
    eax = edx + (edx >> 31)
    edx = ecx
    eax = (eax * 0x3938700) & 0xffffffff
    edx = (edx * 0x989681) & 0xffffffff
    edx = edx - eax

    # print(f'esi {hex(result2)}, edx {hex(edx)}')

    if edx == result2:
        print(f'stage 2 pass {serial}')
        pass
    else:
        return


# ------------------------------------------------------
# 逆向時候遇到的 sub_44D2A0 函數，他會吸收一個字符串，進行一些奇怪的運算然後返回一個 16 位整數。
# moved_serial: 經過重排的待測激活碼
# count: 待測激活碼的前幾位才參與運算
# data_strange_op8: eax 經過八次奇怪的操作之後得到的值，也提前計算好以便查表了
# 返回值：一個 16 位整數
# ------------------------------------------------------
def sub_44D2A0(moved_serial, count, data_strange_op8):
    result = 0  # WORD 16 bit
    for ecx in range(count):
        ax = ord(moved_serial[ecx]) & 0xffff
        ax = (ax << 8) & 0xffff
        result = (result ^ ax) & 0xffff

        # eax = result
        # for _ in range(8):
        #    eax = data_strange_op[eax]
        result = data_strange_op8[result]
    return result & 0xffff


# ------------------------------------------------------
# 網上抄的，據説可以轉換成無符號數，但是並沒有用到
# ------------------------------------------------------
def unsigned32(signed):
    return signed % 0x100000000


# ------------------------------------------------------
# 將原有的激活碼重排順序
# target: 待重排的字符串
# 返回值：重拍過後的字符串
# ------------------------------------------------------
def change_order(target):
    order = [0, 1, 5, 3, 0xA, 8, 7, 2, 6, 9, 4]
    result = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    # result = ''
    for i in range(len(order)):
        result[i] = target[order[i]]
        # result += target[order[i]]
    return ''.join(result)  # .upper()


# ------------------------------------------------------
# 逆向的時候遇到的 44D390 函數，會將一個字符串計算成一個整數，的原有實現，在本程序中用來提前計算，以便查表
# target: 待計算的字符串
# count: 字符串的前幾位有效
# 返回值：一個整數
# ------------------------------------------------------
def calc_a_value(target, count):
    # print(target)
    if count <= 0:
        return 0

    result = 0
    for i in range(count):
        if target[i].isdigit():
            result = ord(target[i]) + 36 * result - 22
        else:
            # result = ord(target[i].upper()) + 36 * result - 65
            result = ord(target[i]) + 36 * result - 65
    return result


def strange_op(eax):
    if (eax & 0x8000) == 0:
        eax += eax
        eax &= 0xffff  # ffff
    else:
        eax += eax
        eax &= 0xffff  # ffff
        eax ^= 0x1021
        eax &= 0xffff
    return eax


ORIGIN = 'E0E0J0QC1A0'
LIST = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
data_calc_a_value2 = {}
data_calc_a_value4 = {}
data_strange_op = {}
data_strange_op8 = {}


# ------------------------------------------------------
# 將上面那些經常用到的運算結果提前窮舉出來，加快運算速度
# ------------------------------------------------------
def prepare_data():
    def foo4(l):
        yield from itertools.product(*([l] * 4))

    def foo2(l):
        yield from itertools.product(*([l] * 2))

    print('preparing data')
    start = time.time()
    for comb in foo4(LIST):
        text = ''.join(comb)
        data_calc_a_value4.update({text: calc_a_value(text, 4)})
    for comb in foo2(LIST):
        text = ''.join(comb)
        data_calc_a_value2.update({text: calc_a_value(text, 2)})
    print(f'data_calc_a_value ok {time.time() - start}')
    for eax in range(65536):
        data_strange_op.update({eax: strange_op(eax)})
    for eax in range(65536):
        eaxfinal = eax
        for _ in range(8):
            eaxfinal = data_strange_op[eaxfinal]
        data_strange_op8.update({eax: eaxfinal})

    print(f'data_strange_op ok {time.time() - start}')


def task(count, a, b, c, d):
    for _ in range(count):
        test = 'E0' + ''.join(random.choices(LIST, k=9))
        calc(test, a, b, c, d)


def foo2(l):
    yield from itertools.product(*([l] * 2))


if __name__ == '__main__':
    prepare_data()
    #start = time.time()
    #for _ in range(1000000):
    #    calc(ORIGIN, data_calc_a_value2, data_calc_a_value4, data_strange_op, data_strange_op8)
    #print(time.time() - start)
    #exit(0)

    now = time.time()
    processes = []
    print(f'You have {multiprocessing.cpu_count()} CPUs')
    for i in range(multiprocessing.cpu_count() - 1):
        p = multiprocessing.Process(target=task, args=(
            10000000000, data_calc_a_value2, data_calc_a_value4, data_strange_op, data_strange_op8))
        processes.append(p)
        p.start()

    for process in processes:
        process.join()
    print(time.time() - now)
