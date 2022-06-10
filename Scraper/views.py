import csv
import datetime
import glob
import os
import re
import sys
import traceback
from py_linq import Enumerable
from django.contrib import messages
from django.shortcuts import render, redirect

import categories
from categories import Categories
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC


def home(request):
    if request.method == 'POST' or request.FILES:
        postData = request.POST
        cat_name = postData.get('catName')
        if cat_name:
            proUrls = []
            if request.FILES:
                csvReader = request.FILES['file']
                for i in csvReader:
                    proUrls.append(str(i.decode('UTF-8')).strip())
            else:
                proUrls = list(postData.get('urls').split(','))

            if proUrls:
                driver = GetDriver()
                if driver == False:
                    messages.warning(request, "Error Initializing Chrome Driver...!\nPlease Try Again...|")
                    return redirect('home')
                resp = ParsedProducts(request, cat_name, proUrls, driver)
                if resp[0] == False:
                    messages.warning(request, "Error Parsing Product(s)...!")
                    return redirect('home')
                else:
                    messages.success(request, "Product(s) Parsed Successfully...!")
                    return redirect('home')
            else:
                messages.warning(request, "Please Enter Product Url(s)...!")
                return redirect('home')
        else:
            messages.warning(request, "Please Select Category...!")
            return redirect('home')
    else:
        file = getLatestFile()
        context = {'categories': Categories, 'file': file}
        return render(request, 'index.html', context)


def ParsedProducts(request, cat, urls, driver):
    proData = []
    hasLogined = []
    for url in urls:
        try:
            if 'ng-mobile.de' in url:
                storeUrl = 'https://www.ng-mobile.de'
            elif 'otara.de' in url:
                storeUrl = 'https://otara.de'
            else:
                storeUrl = ''
                continue

            loggedUrl = Enumerable(hasLogined).where(lambda x: x == storeUrl).first_or_default()
            if not loggedUrl:
                AccountLogin(storeUrl, hasLogined, driver)

            driver.get(url)

            WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, "//h1[@itemprop='name']")))

            name = str(driver.find_element_by_xpath("//h1[@itemprop='name']").text.strip())
            price = driver.find_element_by_xpath(
                "//span[@class='price--content content--default']/meta[@itemprop='price']").get_attribute("Content")
            delivery = str(driver.find_element_by_xpath(
                "//div[@class='buybox--inner']//span[contains(@class,'delivery--text')]").text).replace("\n",
                                                                                                        " ").replace(
                "\r", "")

            print(name, " - ", price, " - ", delivery)

            proData.append([cat, url, name, price, delivery])
        except Exception as e:
            print(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
            continue
    csvPath = ''
    if proData:
        try:
            filePath = os.path.dirname(os.path.abspath(__file__)).rsplit('\\', 1)[0].split('\\')
            filePath = os.path.join('\\'.join(filePath), 'static')
            csvPath = 'ScrapedResults_' + str(datetime.datetime.now().strftime('%Y-%m-%d %H-%M')) + '.csv'
            csvPath = os.path.join(filePath, csvPath)
            with open(csvPath, 'w', encoding='UTF8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Category', 'ProductUrl', 'Name', 'Price', 'Delivery'])
                writer.writerows(proData)
        except Exception as e:
            print(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
            return False, None

    return True, csvPath


def AccountLogin(storeUrl, hasLogined, driver):
    try:
        with open('StoreCredentials.csv', 'r', encoding='UTF8', newline='') as f:
            csvReader = csv.reader(f)
            next(csvReader)
            userData = list(csvReader)

            storeData = Enumerable(userData).where(lambda x: storeUrl in x[0]).first_or_default()

            driver.get(storeUrl + "/account")
            hasLogined.append(storeUrl)

            try:
                WebDriverWait(driver, 5).until(EC.visibility_of_element_located(
                    (By.XPATH, "//div[@class='register--login-email']//input[@name='email']")))
            except:
                try:
                    WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//div[contains(@class,'account--welcome panel')]")))
                except:
                    return

            try:
                driver.find_element_by_xpath("//a[contains(@class,'cookie-permission--accept')]").click()
            except:
                pass

            driver.find_element_by_xpath("//div[@class='register--login-email']//input[@name='email']").send_keys(
                storeData[1])
            driver.find_element_by_xpath("//div[@class='register--login-password']//input[@name='password']").send_keys(
                storeData[2])
            driver.find_element_by_xpath("//div[@class='sdkAutoLogin--panel']//input[@name='sdkAutoLogin']").click()
            driver.find_element_by_xpath("//div[@class='register--login-action']//button[@name='Submit']").click()

            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'account--welcome panel')]")))
    except Exception as e:
        print(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        return False


def category(request):
    csvPath = ''
    if request.method == 'POST':
        postData = request.POST
        cat_name = postData.get('catname')
        if cat_name:
            SaveToPY(cat_name)
            messages.success(request, "Category Added Successfully...!")
        else:
            messages.warning(request, "Please Enter Category...!")

        return redirect('category')
    else:
        if Categories:
            try:
                filePath = os.path.join(
                    '\\'.join(os.path.dirname(os.path.abspath(__file__)).rsplit('\\', 1)[0].split('\\')), 'static')
                csvPath = os.path.join(filePath, 'Categories.csv')
                with open(csvPath, "w", encoding='UTF8', newline='') as fp:
                    writer = csv.writer(fp)
                    for i in Categories:
                        writer.writerow([i])
            except:
                pass
        context = {'filePath': csvPath}
        return render(request, 'category.html', context)


def SaveToPY(category_Name):
    Categories.extend([category_Name])
    Categories.sort(reverse=False)
    try:
        with open('categories.py', 'r+', encoding='UTF8', newline='') as f:
            f.write("Categories = " + str(Categories))
    except Exception as e:
        print(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))


def getLatestFile():
    try:
        filePath = os.path.join('\\'.join(os.path.dirname(os.path.abspath(__file__)).rsplit('\\', 1)[0].split('\\')))
        return max(glob.glob(os.path.join(filePath, "static/ScrapedResults*")), key=os.path.getctime)
    except:
        return ''


def uploadCsvCategories(request):
    csvCategories = []
    if request.method == 'POST' or request.FILES:
        csvCategory = request.FILES['csvCat']
        for i in csvCategory:
            csvCategories.append(str(i.decode('UTF-8')).strip())

        newCat = []
        for j in csvCategories:
            matchedCat = Enumerable(Categories).where(lambda x: str(x).lower() == str(j).lower()).first_or_default()
            if matchedCat is None:
                newCat.append(j)
        if newCat:
            SaveToPY(",".join(newCat))
            messages.success(request, 'CSV Categories Uploaded Successfully..!')
        else:
            messages.success(request, 'Categories Already Existed..!')
        return redirect('category')
    else:
        return render(request, 'category.html')


def GetDriver():
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-dev-shm-usag')
        chrome_options.add_argument('disable-infobars')
        chrome_options.add_argument('--disable-browser-side-navigation')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option('prefs', {'intl.accept_languages': 'en,en_US'})
        chrome_options.add_argument("window-size=1280,800")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36")
        chrome_options.add_argument("--ignore-certificate-errors")
        return webdriver.Chrome(ChromeDriverManager().install(), chrome_options=chrome_options)
    except Exception as e:
        print(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        return False