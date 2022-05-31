'''
尋找 D.C.4 ダ・カーポ 4 游戲的所有激活碼的程序。

Author: 冬夜 @esuOneGov, esuOneGov@galgamer.eu.org

本程序工作原理：
直接窮舉 11 位的序列號肯定是不現實的，所以我利用游戲對序列號的判定機制進行分段窮舉。

 0. 序列號會在一開始進行重新排列，因此下面的所説的 serial 都是重排過的，
    待我們找到真正的序列號之後會重排回來。

 1. 我們發現，序列號的開頭的兩位，即 serial[0:2] 肯定是 E0

 2. 我們發現，序列號判定機制的 stage2 只對序列號的中間五位，即 serial[2:7] 的判斷
    不和其他位有關，因此先對這五位進行窮舉，讓他滿足 stage2，這樣計算量比較能接受。

 3. 接下來就是 stage1 會校驗的序列號后四位，即 serial[7:11]，的時候，第 2 步的
    serial[2:7] 也會參與運算，所以這裏運算量比較大，進行了一些優化。

 4. 執行完上面的四步，生成的激活碼必定可以通過 stage1 到 stage3.

運行這個程序分別需要 1.5G 的磁盤空間和 RAM 空間，完整跑完一次需要大約五分鐘。
'''
import time, itertools, sqlite3


# 以下是在 reverseDC4.py 中實現的判斷函數，暫且複製過來

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


def sub_44D2A0(moved_serial, count):
    result = 0  # WORD 16 bit
    for ecx in range(count):
        ax = ord(moved_serial[ecx]) & 0xffff
        ax = (ax << 8) & 0xffff
        result = (result ^ ax) & 0xffff

        result = data_strange_op8[result]
    return result & 0xffff


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


# 以上是在 reverseDC4.py 中實現的判斷函數，暫且複製過來

# ------------------------------------------------------
# 用於生成窮舉的序列值，比如 000 001 002 ... ZZY ZZZ
# list: 生成時使用的字母表
# length: 生成的序列長度
# 返回值：沒有，這是一個迭代器
# ------------------------------------------------------
def gen_product(list, length):
    yield from itertools.product(*([list] * length))


# ------------------------------------------------------
# 給定一個 serial[2:7] 來計算 stage1 驗證中的 edx，就是 44D500 処用來比較的那個
# str2to7: 經過重排的序列號的 第二到第七位 字符串
# 返回值：edx 中的整數
# ------------------------------------------------------
def calc_stage1_edx_for_2to7(str2to7):
    result4 = sub_44D2A0('E0' + str2to7, 7)

    # 44d4e8
    multiple = result4 * 0x51eb851f
    # eax = multiple & 0xffffffff
    edx = ((multiple >> 32) & 0xffffffff) >> 3
    eax = edx + (edx >> 31)
    edx = result4 - eax
    edx = (edx * 0x19) & 0xffffffff
    edx += result4
    return edx


# ------------------------------------------------------
# 測試一個給定的 serial[2:7] 能不能通過 stage2 的驗證
# str2to7: 經過重排的序列號的 第二到第七位 字符串
# 返回值：True 或者 False
# ------------------------------------------------------
def stage2test(str2to7):
    # stage 2 44D519

    result2 = calc_a_value(str2to7, 5)  # esi
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
        return True
    else:
        return False


# ------------------------------------------------------
# 把 serial[2:7] 中每種可能的組合進行窮舉，並分別 calc_stage1_edx_for_2to7 計算 edx
# 把這兩項結果保存進數據庫，以便之後的使用
# 返回值：沒有
# ------------------------------------------------------
def stage2gen():
    # init db
    DB = sqlite3.connect(':memory:', check_same_thread=False)
    DB.execute('CREATE TABLE IF NOT EXISTS str2to7 (valid TEXT PRIMARY KEY, edx INTEGER)')
    DB.execute('CREATE TABLE IF NOT EXISTS realSerial (valid TEXT PRIMARY KEY)')
    DB.commit()

    for comb in gen_product(LIST, 5):
        str2to7 = ''.join(comb)
        if stage2test(str2to7):
            edx = calc_stage1_edx_for_2to7(str2to7)
            DB.execute('INSERT INTO str2to7 (valid, edx) VALUES (?,?)', (str2to7, edx))

    DB.execute('CREATE UNIQUE INDEX IF NOT EXISTS str2to7toEBX ON str2to7 (valid)')
    DB.commit()
    count = DB.execute('SELECT count(valid) FROM str2to7').fetchall()
    print(f'{count} serial[2:7] found.')

    # copy to hdd
    DB_hdd = sqlite3.connect(DB_FILE)
    DB.backup(DB_hdd)
    DB_hdd.commit()
    DB_hdd.close()
    DB.close()


# ------------------------------------------------------
# 將被重排順序的序列號還原成原有順序。
# target: 被重排的序列號
# 返回值：原有的序列號
# ------------------------------------------------------
def unchange_order(target):
    reverse_order = [0, 1, 7, 3, 0xA, 2, 8, 6, 5, 9, 4]
    result = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    # result = ''
    for i in range(len(reverse_order)):
        result[i] = target[reverse_order[i]]
        # result += target[order[i]]
    return ''.join(result)  # .upper()


# ------------------------------------------------------
# 將 stage2gen 中找到的所有 serial[2:7]，分別找到對應的 serial[7:11] 最後四位
# 然後組成完整的激活碼，還原順序保存到數據庫
# 返回值：沒有
# ------------------------------------------------------
def stage1gen():
    DB_memory = sqlite3.connect(':memory:')
    DB_hdd = sqlite3.connect(DB_FILE)
    DB_hdd.backup(DB_memory)
    DB_hdd.close()

    # ------------------------------------------------------
    # 爲了快速通過 serial[2:7] 找到 serial[7:11]，使用提前運算好的值直接查表，可以節省上千萬次的運算時間。
    # 首先通過事先建好的數據庫查到 serial[2:7] 和對應的 edx，因爲 edx 要和 result3 相同才能進入 stage2，
    # 所以使用 result3 反查對應可能的 serial[7:11]，
    # 使用事先準備的 find_7to11_from_value4 避免進行窮舉運算。
    # ------------------------------------------------------
    cursor = DB_memory.cursor()
    cursor.execute('select * from str2to7')
    for (str2to7, edx) in cursor:
        str7to11_array = find_7to11_from_value4[edx]
        for str7to11 in str7to11_array:
            serial = unchange_order('E0' + str2to7 + str7to11)
            DB_memory.execute('INSERT INTO realSerial (valid) values (?)', (serial,))
    # print('iteration ok')
    DB_memory.commit()
    # print('commited')
    DB_hdd = sqlite3.connect('full.db')
    with DB_hdd:
        DB_memory.backup(DB_hdd, pages=1000, progress=progress)
    DB_hdd.commit()
    DB_hdd.close()
    # print('hdd closed')
    DB_memory.close()
    # print('mem closed')


# ------------------------------------------------------
# 顯示數據庫保存到硬盤上時候的進度
# ------------------------------------------------------
def progress(status, remaining, total):
    print(f'保存中 {total - remaining} / {total} ...')


# 生成序列號的字母表
LIST = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# 使用的主數據庫
DB_FILE = 'serial2.db'  # 硬盤上的
DB = None  # memory 的

# 儲存 對 eax 進行了一次奇怪操作的結果
data_strange_op = {}

# 儲存 對 eax 進行了 8 次奇怪操作的結果
data_strange_op8 = {}

# 通過 (result3) 反查對應的 7to11
find_7to11_from_value4 = {}


# ------------------------------------------------------
# 將上面那些經常用到的運算結果提前窮舉出來，加快運算速度
# ------------------------------------------------------
def prepare_data():
    print('Preparing data')
    start = time.time()

    # 準備 find_7to11_from_value4 的值
    # find_7to11_from_value4 的結構如下
    # {
    #     result3 的某個值1: [對應的str7to11, 對應的str7to11, ...],
    #     result3 的某個值2: [對應的str7to11, 對應的str7to11, ...],
    #     result3 的某個值3: [對應的str7to11, 對應的str7to11, ...],
    #     result3 的某個值4: [對應的str7to11, 對應的str7to11, ...],
    #     ......
    # }
    for comb in gen_product(LIST, 4):
        str7to11 = ''.join(comb)
        value4 = calc_a_value(str7to11, 4)
        if value4 in find_7to11_from_value4:
            find_7to11_from_value4[value4].append(str7to11)
        else:
            find_7to11_from_value4.update({value4: [str7to11]})

    # 提前計算 eax 經過八次奇怪的 strange_op 操作后的運算結果
    # 放在 data_strange_op8 裏以便查表
    for eax in range(65536):
        data_strange_op.update({eax: strange_op(eax)})
    for eax in range(65536):
        eaxfinal = eax
        for _ in range(8):
            eaxfinal = data_strange_op[eaxfinal]
        data_strange_op8.update({eax: eaxfinal})

    print(f'Data prepare finished, time: {time.time() - start}')


if __name__ == '__main__':
    prepare_data()
    start_stage2 = time.time()
    print('正在窮舉 stage2，打開任務管理器查看進度，當本程序占用 RAM 到達 730M 時本階段結束。')
    stage2gen()
    print(f'stage2 窮舉完成, 耗時 {time.time() - start_stage2}')
    start_stage1 = time.time()
    print('正在窮舉 stage1，打開任務管理器查看進度，當本程序占用 RAM 到達 1310M 時本階段結束。')
    stage1gen()
    print(f'stage1 窮舉完成, 耗時 {time.time() - start_stage1}')
    print(f'所有激活碼在 full.db')
    exit(0)
