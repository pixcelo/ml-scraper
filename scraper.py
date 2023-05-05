import configparser
from discord_webhook import DiscordWebhook
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions

class Scraper:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")

        self.WEBHOOK_URL = self.config.get('discord', 'webhook_url')
        self.USER_NAME = self.config.get("login", "username")
        self.PASS_WORD = self.config.get("login", "password")

        edge_options = EdgeOptions()
        edge_options.headless = False
        self.driver = webdriver.Edge(executable_path="path/to/msedgedriver.exe", options=edge_options)

    def send_error_notification(self, error_message: str):
        webhook = DiscordWebhook(url=self.WEBHOOK_URL, content=f'An error occurred: {error_message}')
        webhook.execute()

    def login(self):
        driver = self.driver
        driver.get("https://kabu.click-sec.com/cfd/trade.do")
        driver.find_element(By.NAME, "j_username").send_keys(self.USER_NAME)
        driver.find_element(By.NAME, "j_password").send_keys(self.PASS_WORD)

        login_button = driver.find_element(By.XPATH, "//button[@value='Login']")
        login_button.click()

        link_element = driver.find_element(By.CLASS_NAME, "js-cfd")
        link_element.click()

    def get_financial_data(self):
        driver = self.driver
        driver.get("https://www.rakuten-sec.co.jp/web/market/data/us10yt.html")
        iframe = driver.find_element(By.ID, "ifr")
        driver.switch_to.frame(iframe)
        ten_years_bond = driver.find_element(By.XPATH, '//*[@id="cBond"]/table[1]/tbody/tr[1]/td/em')
        bond_text = driver.execute_script("return arguments[0].textContent;", ten_years_bond)

        return {"ten_years_bond": float(bond_text.replace('％', '')) / 100}

    def exists_open_interest(self):
        driver = self.driver
        local_storage_data = {
            'cfd.228435341.introduction-modal-flag': 'false',
            'cfd.228435341.order-tab-select': '2',
            'cfd.228435341.cfd-product-code': '00003060000',
        }

        for key, value in local_storage_data.items():
            driver.execute_script(f"window.localStorage.setItem('{key}', '{value}');")

        driver.refresh()

        iframe = driver.find_element(By.ID, "iframe_trade")
        driver.switch_to.frame(iframe)

        speed_order_element = driver.find_element(By.ID, "react-tabs-14")
        speed_order_element.click()

        sell_oi = driver.find_element(By.XPATH, '//*[@id="react-tabs-15"]/div/div[3]/div[3]/div/div[5]/div/div[1]/label')
        buy_oi = driver.find_element(By.XPATH, '//*[@id="react-tabs-15"]/div/div[3]/div[3]/div/div[5]/div/div[3]/label')

        return {"sell": sell_oi.text, "buy": buy_oi.text}

    def place_order(self, side, amount):
        driver = self.driver
        lot_button = driver.find_element(By.XPATH, '//*[@id="react-tabs-15"]/div/div[3]/div[4]/div[2]/div/div[2]/button[1]')
        lot_button.click()

        sell_button = driver.find_element(By.XPATH, '//*[@id="react-tabs-15"]/div/div[3]/div[2]/div[1]/div[1]/div/label')
        buy_button = driver.find_element(By.XPATH, '//*[@id="react-tabs-15"]/div/div[3]/div[2]/div[1]/div[2]/div/label')

        if side == "Buy":
            buy_button.click()
        else:
            sell_button.click()