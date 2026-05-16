import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_hot_topics_page():
    """调试热搜榜页面"""
    logger.info("="*60)
    logger.info("调试热搜榜页面")
    logger.info("="*60)
    
    # 初始化浏览器
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    try:
        # 访问热搜榜
        url = "https://s.weibo.com/top/summary"
        logger.info(f"访问URL: {url}")
        
        driver.get(url)
        time.sleep(5)
        
        # 检查当前URL
        logger.info(f"当前URL: {driver.current_url}")
        
        # 检查页面标题
        logger.info(f"页面标题: {driver.title}")
        
        # 检查页面源码长度
        page_source_length = len(driver.page_source)
        logger.info(f"页面源码长度: {page_source_length} 字符")
        
        # 保存页面源码
        with open('debug_hot_topics_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.info("页面源码已保存到: debug_hot_topics_page.html")
        
        # 检查是否被重定向
        if 'visitor' in driver.current_url or 'passport' in driver.current_url:
            logger.warning("⚠️ 页面被重定向到访客系统或登录页面")
            logger.info("尝试等待10秒...")
            time.sleep(10)
            
            # 刷新页面
            driver.refresh()
            time.sleep(5)
            
            # 再次检查
            logger.info(f"刷新后URL: {driver.current_url}")
            logger.info(f"刷新后标题: {driver.title}")
            
            # 再次保存页面源码
            with open('debug_hot_topics_page_refreshed.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            logger.info("刷新后页面源码已保存到: debug_hot_topics_page_refreshed.html")
        
        # 滚动页面
        logger.info("\n滚动页面...")
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        
        time.sleep(3)
        
        # 再次保存页面源码
        with open('debug_hot_topics_page_scrolled.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.info("滚动后页面源码已保存到: debug_hot_topics_page_scrolled.html")
        
        # 解析页面
        logger.info("\n开始解析页面...")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 查找所有可能的元素
        logger.info("\n查找热搜榜相关元素:")
        
        # 方法1: list_a
        list_a = soup.find('ul', class_='list_a')
        if list_a:
            logger.info("✅ 找到 list_a 元素")
            list_items = list_a.find_all('li')
            logger.info(f"  包含 {len(list_items)} 个列表项")
            
            if list_items:
                for i, item in enumerate(list_items[:5], 1):
                    logger.info(f"  第{i}项: {item.get_text()[:100]}")
        else:
            logger.warning("❌ 未找到 list_a 元素")
        
        # 方法2: 查找所有ul元素
        uls = soup.find_all('ul')
        logger.info(f"\n找到 {len(uls)} 个ul元素")
        for i, ul in enumerate(uls[:5], 1):
            logger.info(f"  ul#{i}: class='{ul.get('class')}', 包含{len(ul.find_all('li'))}个li")
        
        # 方法3: 查找所有包含"热搜"的元素
        logger.info("\n查找包含'热搜'的元素:")
        hot_elements = soup.find_all(string=lambda text: text and '热搜' in text)
        logger.info(f"找到 {len(hot_elements)} 个包含'热搜'的文本")
        for i, elem in enumerate(hot_elements[:5], 1):
            logger.info(f"  {i}. {elem.strip()[:100]}")
        
        # 方法4: 查找所有链接
        logger.info("\n查找所有链接:")
        links = soup.find_all('a')
        logger.info(f"找到 {len(links)} 个链接")
        for i, link in enumerate(links[:10], 1):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if text:
                logger.info(f"  {i}. {text[:50]} -> {href[:80]}")
        
        # 方法5: 查找所有class包含"hot"的元素
        logger.info("\n查找class包含'hot'的元素:")
        hot_elements = soup.find_all(class_=lambda x: x and 'hot' in str(x).lower())
        logger.info(f"找到 {len(hot_elements)} 个包含'hot'的元素")
        for i, elem in enumerate(hot_elements[:5], 1):
            logger.info(f"  {i}. class='{elem.get('class')}', text={elem.get_text()[:50]}")
        
        # 方法6: 查找所有class包含"top"的元素
        logger.info("\n查找class包含'top'的元素:")
        top_elements = soup.find_all(class_=lambda x: x and 'top' in str(x).lower())
        logger.info(f"找到 {len(top_elements)} 个包含'top'的元素")
        for i, elem in enumerate(top_elements[:5], 1):
            logger.info(f"  {i}. class='{elem.get('class')}', text={elem.get_text()[:50]}")
        
        # 方法7: 查找所有class包含"rank"的元素
        logger.info("\n查找class包含'rank'的元素:")
        rank_elements = soup.find_all(class_=lambda x: x and 'rank' in str(x).lower())
        logger.info(f"找到 {len(rank_elements)} 个包含'rank'的元素")
        for i, elem in enumerate(rank_elements[:5], 1):
            logger.info(f"  {i}. class='{elem.get('class')}', text={elem.get_text()[:50]}")
        
        # 方法8: 查找所有class包含"list"的元素
        logger.info("\n查找class包含'list'的元素:")
        list_elements = soup.find_all(class_=lambda x: x and 'list' in str(x).lower())
        logger.info(f"找到 {len(list_elements)} 个包含'list'的元素")
        for i, elem in enumerate(list_elements[:5], 1):
            logger.info(f"  {i}. class='{elem.get('class')}', text={elem.get_text()[:50]}")
        
        logger.info("\n" + "="*60)
        logger.info("调试完成")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"调试过程出错: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        
    finally:
        time.sleep(5)
        driver.quit()
        logger.info("浏览器已关闭")

if __name__ == '__main__':
    debug_hot_topics_page()
