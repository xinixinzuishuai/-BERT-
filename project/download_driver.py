import os
import zipfile
import requests
from pathlib import Path

def download_chromedriver_v2():
    """使用 Chrome for Testing 下载 ChromeDriver"""
    # Chrome 145 版本
    chrome_version = "145.0.7632.77"
    
    # Chrome for Testing 官方下载地址
    download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{chrome_version}/win64/chromedriver-win64.zip"
    
    # 下载目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(project_dir, "chromedriver-win64.zip")
    driver_path = os.path.join(project_dir, "chromedriver.exe")
    
    print(f"正在下载 ChromeDriver {chrome_version}...")
    print(f"下载地址: {download_url}")
    
    try:
        # 下载文件
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"\r下载进度: {progress:.1f}%", end='')
        
        print("\n✅ 下载完成！")
        
        # 解压文件
        print("正在解压...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(project_dir)
        
        # 查找 chromedriver.exe
        extracted_dir = os.path.join(project_dir, "chromedriver-win64")
        if os.path.exists(extracted_dir):
            extracted_driver = os.path.join(extracted_dir, "chromedriver.exe")
            if os.path.exists(extracted_driver):
                import shutil
                shutil.move(extracted_driver, driver_path)
                shutil.rmtree(extracted_dir)
        
        # 删除 zip 文件
        os.remove(zip_path)
        
        if os.path.exists(driver_path):
            print(f"✅ ChromeDriver 已成功安装到: {driver_path}")
            return True
        else:
            print("❌ 解压失败，未找到 chromedriver.exe")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 下载失败: {e}")
        print("\n正在尝试备用下载方式...")
        return download_chromedriver_alternative()
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        return False

def download_chromedriver_alternative():
    """备用下载方式：使用 npmmirror 的最新版本"""
    print("\n尝试下载最新版本的 ChromeDriver...")
    
    # 使用最新版本
    download_url = "https://cdn.npmmirror.com/binaries/chromedriver/LATEST_RELEASE"
    
    try:
        response = requests.get(download_url, timeout=10)
        if response.status_code == 200:
            version = response.text.strip()
            print(f"最新版本: {version}")
            
            download_url = f"https://cdn.npmmirror.com/binaries/chromedriver/win64/{version}/chromedriver-win64.zip"
            print(f"下载地址: {download_url}")
            
            project_dir = os.path.dirname(os.path.abspath(__file__))
            zip_path = os.path.join(project_dir, "chromedriver-win64.zip")
            driver_path = os.path.join(project_dir, "chromedriver.exe")
            
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print("✅ 下载完成！")
            
            # 解压
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(project_dir)
            
            extracted_dir = os.path.join(project_dir, "chromedriver-win64")
            if os.path.exists(extracted_dir):
                extracted_driver = os.path.join(extracted_dir, "chromedriver.exe")
                if os.path.exists(extracted_driver):
                    import shutil
                    shutil.move(extracted_driver, driver_path)
                    shutil.rmtree(extracted_dir)
            
            os.remove(zip_path)
            
            if os.path.exists(driver_path):
                print(f"✅ ChromeDriver 已成功安装到: {driver_path}")
                print(f"⚠️  注意：下载的是 {version} 版本，可能与你的 Chrome 145 不完全兼容")
                return True
            
        return False
        
    except Exception as e:
        print(f"❌ 备用下载也失败: {e}")
        return False

if __name__ == "__main__":
    success = download_chromedriver_v2()
    if success:
        print("\n现在可以运行 python weibo_spider.py 了！")
    else:
        print("\n请按照提示手动下载 ChromeDriver")
        print("\n手动下载步骤:")
        print("1. 访问 Chrome for Testing: https://googlechromelabs.github.io/chrome-for-testing/")
        print("2. 选择 Stable 版本，下载 Windows 64 位的 chromedriver")
        print("3. 解压后将 chromedriver.exe 放到项目目录")
