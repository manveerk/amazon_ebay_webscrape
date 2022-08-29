import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import psycopg2 
from matplotlib import pyplot as plt

#User input
searchString = input('Please enter the item you want to search: ') 
priceLowerLimit= input('Please enter the lower price limit for the item you are looking for: ') 
priceUpperLimit= input('Please enter the upper price limit for the item you are looking for: ') 
searchRating = input('What is the optimum rating of product, from 0.0 to 5.0, that you are looking for? ')
searchTotalRatings = input('What is the minimum number of ratings you would like the product to have? ')

# Provide db connection details
t_host = "localhost" 
t_port = "5432" 
t_dbname = "postgres"
t_user = "postgres"
t_pw = ""

#### Creating database connection
db_conn = psycopg2.connect(host=t_host, port=t_port, dbname=t_dbname, user=t_user, password=t_pw)
db_cursor = db_conn.cursor()
db_cursor.execute('select version()')
data = db_cursor.fetchone()
print("Connection established to: ",data)
db_cursor.execute('''drop table if exists scraped_data;''')
db_cursor.execute('''create table scraped_data(item_name varchar(500), item_rating decimal(2,1), number_of_ratings int, 
                  item_price decimal(10,2), delivery_date varchar(50), item_url varchar(2000))''')


#################
#provide chrome driver path
chrome_driver_path = '/Users/manveerkaur/Documents/Database_Systems/DatabaseProject/chromedriver'
delay = 15
#initialize chrome browser
driver = webdriver.Chrome(executable_path=chrome_driver_path)

#PLaunch amazon.com on chrome
driver.get('https://www.amazon.com/')
driver.find_element_by_id('twotabsearchtextbox').send_keys(searchString)
driver.find_element_by_id('nav-search-submit-button').click()

#function to extract text from web elements
def extract_text(soup_obj, tag, attribute_name, attribute_value):
	txt = soup_obj.find(tag,{attribute_name: attribute_value}).text.strip() if soup_obj.find(tag,{attribute_name: attribute_value}) else ''
	return txt

rows = []
try:
	WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.XPATH,"//*[@class='a-dropdown-prompt']")))
except TimeoutException:
	print('Time out loading page')
	
else:
    for x in range (0,5):
         
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.XPATH,"//div[@data-component-type='s-search-result']")))
        # parse the html using beautiful soup and store in variable `soup`
        soup = BeautifulSoup(driver.page_source,'html.parser')
        item_list=soup.find_all('div',{'data-component-type': 's-search-result'})
        
        url_counter=1
        for item in item_list:
            item_title = extract_text(item, 'span', 'class', 'a-size-medium a-color-base a-text-normal')
            
            item_rating = extract_text(item,'a', 'class', 'a-popover-trigger a-declarative')
            if "stars" not in item_rating:
                rating=0.0
            else:
                rating = list(map(float,re.findall('\d*\.?\d+',item_rating)))[0]
            item_price = extract_text(item,'span', 'class', 'a-offscreen')
            if "$" not in item_price:
                price=0.0
            else:
                price = float(item_price.replace('$', '').replace(',', ''))
            item_total_ratings = extract_text(item,'span','class', 'a-size-base')
            
            if item_total_ratings=='':
                total_ratings=0
            elif "," not in item_total_ratings:
                total_ratings= int(item_total_ratings) 
            else:
                total_ratings=int(item_total_ratings.replace(",", ""))
                
            item_url_tag = soup.find_all('a',{'class': 'a-link-normal s-underline-text s-underline-link-text a-text-normal'}) 
            item_delivery_date = extract_text(item,'span', 'class', 'a-text-bold')
            url_xpath="(//div[@data-component-type='s-search-result']//a[@class='a-link-normal a-text-normal'])["+str(url_counter)+"]"
            url_counter+=1
            item_url=driver.find_element_by_xpath(url_xpath).get_attribute('href')
            #---------Insert amazon data in table----------
            db_cursor.execute('''Insert into scraped_data(
            item_name,
            item_rating,
            number_of_ratings,
            item_price,
            delivery_date,
            item_url
            )values(%s,%s,%s,%s,%s,%s)''',(
            item_title,
            rating,
            total_ratings,
            price,
            item_delivery_date,
            item_url));
            rows.append([item_title, rating, total_ratings, price, item_delivery_date, item_url])
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.XPATH,"//li[@class='a-last']/a")))
        driver.find_element_by_xpath("//li[@class='a-last']/a").click()

#**********************--------Ebay--------*****************************#    
    
driver.get('https://www.ebay.com/')
driver.find_element_by_id('gh-ac').send_keys(searchString)
driver.find_element_by_id('gh-btn').click()

try:
	WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.XPATH,"//*[@class='srp-results srp-list clearfix']")))
except TimeoutException:
	print('Time out loading page')
	
else:
    for y in range(0,4):
        soup = BeautifulSoup(driver.page_source,'html.parser')
        item_list=soup.find_all('li',{'class': 's-item s-item__pl-on-bottom s-item--watch-at-corner'})
        url_counter=1
        for item in item_list:
            item_title = extract_text(item, 'h3', 'class', 's-item__title')
            item_rating = extract_text(item,'span', 'class', 'clipped')
            if "out of 5 stars" not in item_rating:
                rating=0.0
            else:
                rating=float(item_rating.replace(' out of 5 stars.', ''))
            item_price = extract_text(item,'span', 'class', 's-item__price').replace(',', '')
            #price = float(item_price.replace('$', ''))
            
            price=list(map(float,re.findall('\d*\.?\d+',item_price)))[0]
            item_total_ratings = extract_text(item,'span','class', 's-item__reviews-count')
            if "product" not in item_total_ratings:
                ratings=0
            else:
                ratings = int(item_total_ratings.split(" ")[0])
            item_delivery_date = extract_text(item,'span', 'class', 'POSITIVE BOLD')
            url_xpath="(//li[@class='s-item s-item__pl-on-bottom s-item--watch-at-corner']//a[@class='s-item__link'])["+str(url_counter)+"]"
            url_counter+=1
            item_url=driver.find_element_by_xpath(url_xpath).get_attribute('href')
            #---------Insert ebay data in table----------
            db_cursor.execute('''Insert into scraped_data(
            item_name,
            item_rating,
            number_of_ratings,
            item_price,
            delivery_date,
            item_url
            )values(%s,%s,%s,%s,%s,%s)''',(
            item_title,
            rating,
            ratings,
            price,
            item_delivery_date,
            item_url));
            rows.append([item_title, rating, ratings, price, item_delivery_date, item_url])
        driver.find_element_by_xpath("//a[@class='pagination__next icon-link']").click()


####Query the database#######	
db_cursor.execute('''Select * from scraped_data where item_rating = %s and item_price > %s and item_price < %s and number_of_ratings > %s order by item_price ''',(searchRating, priceLowerLimit, priceUpperLimit, searchTotalRatings))		

records = db_cursor.fetchall()
for row in records:
    print("Item Name = ", row[0],)
    print("Item Rating = ", row[1],)
    print("Total Number of Ratings = ", row[2],)
    print("Item Price = ", row[3],)
    print("Item Url = ", row[5],"\n")

#Store data in csv
columns = ['Item Name', 'Item Rating', 'Total number of ratings', 'Item Price', 'Item Delivery Date', 'Item Url']
df = pd.DataFrame(data=rows, columns=columns)
df.to_csv(
'ItemSearch.csv', index = False)		

#Plot a histogram for price
df['Item Price'].hist(bins=50)		
plt.title('Item Price Chart')
plt.tight_layout()   
db_conn.commit()

driver.quit()
