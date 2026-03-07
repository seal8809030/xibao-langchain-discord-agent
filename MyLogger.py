import logging
import os, re
import contextvars
from datetime import datetime, timedelta
import threading
from logging.handlers import TimedRotatingFileHandler
import traceback

log_lock = threading.Lock()
print_lock = threading.Lock()

log_name = 'Unknown'
log_dir = os.path.dirname(os.path.abspath(__file__))
log_keep_days = 0

# 用於動態捕獲日誌的鉤子 (例如 Discord 介面)
log_callback = contextvars.ContextVar("log_callback", default=None)

log_manger_dict = {}
log_levels = {
    logging.DEBUG: 'Debug',
    logging.INFO: 'Info',
    logging.WARNING: 'Log',
    logging.ERROR: 'Error',
    logging.CRITICAL: 'Critical'
}

def setup_logger(Name: str, Dir: str, Keep_Days: int = 0):
    global log_name, log_dir, log_keep_days
    log_name = Name
    log_dir = Dir
    if Keep_Days > 0: log_keep_days = Keep_Days

class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, level, when='midnight', interval=1, backupCount=0, encoding='utf-8', 
                 separator = "-", log_date_suffix = "%Y%m%d", ext_name = '.log'):
        self.log_dir = log_dir
        self.base_filename = log_name
        self.backupCount = backupCount
        self.level = level
        self.when = when.upper()
        self.interval = interval if self.when != "midnight".upper() else 1  # 記錄 interval 參數
        self.separator = separator
        self.log_date_suffix = log_date_suffix
        self.ext_name = ext_name
        self.prefix = f"{self.base_filename}.{log_levels.get(self.level, 'Log')}{self.separator}"
        self.current_time_suffix = self.get_time_suffix()
        super().__init__(self.get_log_filename(), self.when, self.interval, self.backupCount, encoding=encoding)
        self.suffix = ""
        self.next_rollover_time = self.compute_next_rollover()  # 計算下次輪轉時間

    def get_time_suffix(self):
        """取得當前的時間戳後綴"""
        return datetime.now().strftime(self.log_date_suffix)

    def get_log_filename(self):
        """產生包含時間戳的檔名"""
        return os.path.join(self.log_dir, f"{self.prefix}{self.current_time_suffix}{self.ext_name}")

    def get_timedelta(self):
        delta = timedelta(seconds=0)
        try:
            if self.when == 'S':  # 秒
                delta = timedelta(seconds=self.interval)
            elif self.when == 'M':  # 分鐘
                delta = timedelta(minutes=self.interval)
            elif self.when == 'H':  # 小時
                delta = timedelta(hours=self.interval)
            elif self.when == 'D':  # 天
                delta = timedelta(days=self.interval)
            elif self.when == "midnight".upper(): # 計算下一次午夜時間
                now = datetime.now()  # 獲取當前時間
                midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)  # 今天的午夜時間
                if now >= midnight_today:  # 如果現在時間已經過了午夜
                    next_midnight = midnight_today + timedelta(days=1) # 計算明天的午夜
                else:
                    next_midnight = midnight_today # 計算今天的午夜
                delta = next_midnight - now # 計算距離下一次午夜的時間差
        except:
            ShowErrorLog("[get_timedelta]", traceback.format_exc())
        return delta

    def compute_next_rollover(self):
        """計算下次輪轉的時間"""
        now = datetime.now()
        delta = self.get_timedelta()
        return now + delta

    def doRollover(self):
        current_time = datetime.now()
        # 判斷是否達到下次輪轉時間
        if current_time >= self.next_rollover_time:
            self.current_time_suffix = self.get_time_suffix()
            if self.stream:
                self.stream.close()
                self.stream = None
            # 更新檔案名稱
            self.baseFilename = self.get_log_filename()
            self.stream = self._open()
            # 更新下次輪轉時間
            self.next_rollover_time = self.compute_next_rollover()

            if self.backupCount > 0:
                try:
                    for s in self.getFilesToDelete():
                        os.remove(s)
                except:
                        ShowErrorLog("[doRollover]", traceback.format_exc())

    def getFilesToDelete(self):
        """
        Determine the files to delete when rolling over.

        More specific than the earlier method, which just used glob.glob().
        """
        fileNames = os.listdir(self.log_dir)
        result = []
        prefix = self.prefix
        plen = len(prefix)
        pattern = fr'(?<={self.prefix})(.*)(?=\{self.ext_name})'
        for fileName in fileNames:
            matches = re.findall(pattern, fileName)
            if matches:
                datetime_str = matches[0]  # 直接取第一個匹配結果
                if self.should_delete_file(datetime_str):
                    result.append(os.path.join(self.log_dir, fileName))
        if len(result) < self.backupCount:
            result = []
        else:
            result.sort()
            result = result[:len(result) - self.backupCount]
        return result
    
    def should_delete_file(self, suffix):
        try:
            file_time = datetime.strptime(suffix, self.log_date_suffix)
            current_time = datetime.now()
            time_difference = current_time - file_time
            # 設定間隔的時間差 (例如: 10 秒的 timedelta)
            if self.when == "midnight".upper():
                target_interval = self.get_timedelta() + timedelta(days=1) * (self.backupCount)
            else:
                target_interval = self.get_timedelta() * self.backupCount
            
            # 判斷是否超過 `when` 和 `interval`
            if time_difference > target_interval:
                return True
        except:
            ShowErrorLog(traceback.format_exc())
        return False  # 無法解析的 `suffix` 則忽略


def get_logger(level):
    global log_name, log_dir, log_keep_days

    if level in log_levels:
        logger = logging.getLogger(log_levels.get(level, "Log"))
        
        if not logger.handlers:
            if log_dir and os.path.isdir(log_dir):
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
            logger.setLevel(level)
            file_handler = CustomTimedRotatingFileHandler(level, when='midnight', interval=1, backupCount=log_keep_days)
            file_handler.setLevel(level)
            logger.addHandler(file_handler)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
        return logger

def get_log_str(*args):
    temp_str = f'{datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]} #{os.getpid():5d} '\
               f'{" ".join([str(a).strip() for arg in args for a in arg])}'
    with print_lock:
        print(temp_str)
    return temp_str

def write_into_log(content):
    global log_manger_dict
    log_level = logging.WARNING
    if log_level not in log_manger_dict:
        log_manger_dict[log_level] = get_logger(log_level)
    log_manger_dict[log_level].warning(content)

def ShowLog(*args):
    global log_manger_dict
    log_level = logging.WARNING
    with log_lock:
        if log_level not in log_manger_dict:
            log_manger_dict[log_level] = get_logger(log_level)
        DEBUG_logger = log_manger_dict[log_level]
        content = get_log_str(args)
        DEBUG_logger.warning(content)
        
        # 觸發回調鉤子
        callback = log_callback.get()
        if callback:
            callback(content)

def ShowInfo(*args):
    global log_manger_dict
    log_level = logging.INFO
    with log_lock:
        if log_level not in log_manger_dict:
            log_manger_dict[log_level] = get_logger(log_level)
        INFO_logger = log_manger_dict[log_level]
        content = get_log_str(args)
        INFO_logger.info(content)
        write_into_log(content)

        # 觸發回調鉤子
        callback = log_callback.get()
        if callback:
            callback(content)

def ShowErrorLog(*args):
    global log_manger_dict
    log_level = logging.ERROR
    with log_lock:
        if log_level not in log_manger_dict:
            log_manger_dict[log_level] = get_logger(log_level)
        ERROR_logger = log_manger_dict[log_level]
        content = get_log_str(args)
        ERROR_logger.error(content)
        write_into_log(content)

        # 觸發回調鉤子
        callback = log_callback.get()
        if callback:
            callback(content)

__all__ = ['setup_logger', 'ShowLog', 'ShowInfo', 'ShowErrorLog', 'log_callback']

if __name__ == '__main__':
    import time

    try:
        working_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = working_dir
        os.chdir(working_dir)
    except:
        log_dir = None
    setup_logger(os.path.splitext(os.path.basename(__file__))[0] if '__file__' in globals() else 'Unknown', working_dir)

    for i in range(100):
        ShowLog(i)
        # ShowErrorLog(i)
        time.sleep(1)
