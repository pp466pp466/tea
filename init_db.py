import sqlite3
import os

DB_NAME = "store.db"

def create_and_seed_db():
    """建立資料庫結構並寫入初始測試資料 (若不存在時才寫入)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. 建立服務項目資料表 (services)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL
        )
    ''')

    # 2. 建立價目表資料表 (prices)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            price TEXT NOT NULL,
            category TEXT NOT NULL
        )
    ''')

    # 檢查是否已有資料，無資料才注入初始預設值
    cursor.execute('SELECT COUNT(*) FROM services')
    if cursor.fetchone()[0] == 0:
        services_data = [
            ('嚴選高山茶葉', '來自阿里山與杉林溪高海拔茶區，堅持手採嫩葉與職人烘焙。'),
            ('茶道體驗體驗課', '專業茶師指導，學習沖泡技巧、品茶禮儀與茶藝文化。'),
            ('客製化禮盒包裝', '專為企業送禮與節慶設計，提供質感茶葉禮盒封套客製服務。')
        ]
        cursor.executemany('INSERT INTO services (title, description) VALUES (?, ?)', services_data)

    cursor.execute('SELECT COUNT(*) FROM prices')
    if cursor.fetchone()[0] == 0:
        prices_data = [
            ('特選阿里山烏龍茶 (150g)', '$600 元', '茶葉類'),
            ('凍頂烏龍茶 (150g)', '$550 元', '茶葉類'),
            ('日月潭紅玉紅茶 (100g)', '$480 元', '茶葉類'),
            ('雙罐高山茶禮盒', '$1,280 元', '禮盒類'),
            ('一對一茶藝體驗體驗課 (90min)', '$1,200 元/人', '體驗課程')
        ]
        cursor.executemany('INSERT INTO prices (item_name, price, category) VALUES (?, ?, ?)', prices_data)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_and_seed_db()
    print("SQLite 資料庫已成功檢查並初始化！")