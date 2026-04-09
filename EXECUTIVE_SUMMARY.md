**Executive Summary of Digital Advertising Market Analytics**

**Primary Findings:**

1. Through data cleansing, the overall revenue for the digital advertising market in Amman was **$48,701.50** and the total number of orders was **443**. This means the average order value was **$109.94**.
2. Generally, the city with the highest revenue in Amman compared to other cities within the dataset is Amman.
3. Overall, when comparing order values between different product categories (broadband, computer hardware, etc.) the category with the highest order value was **Books**, specifically **$70**.
4. Both total revenue and total number of orders for each month were relatively stable during most of the data period with notable jumps occurring in both metrics in the final month exhibited in the visual displays.
5. The results did not indicate any statistical relationship between customer city and product category.

**Additional Supportive Data:**

Before progression of the primary analysis, I used test_db.py to perform exploratory data analysis to understand the dataset more thoroughly. During this period, I verified table sizes, determined the number and frequency of each order status, locations with quantities exceeding 100 (indicating abnormal quantity), determined the quality of city, and verified the product categories. This exploratory data analysis aided in the selection of appropriate Key Performance Indicators (KPI).

* The validity of **Finding 1** can be established through the baseline output of analysis.py*
Total Revenue = **$48,701.50**
Valid Orders = **443**
Average Order Value = **$109.94**

* The validity of **Finding 2** can be established through the KPI “Revenue by City” as displayed in the chart revenue_by_city.png.*
The City of Amman exhibited as the highest revenue-producing City in the dataset.

* The validity of **Finding 3** can be established through the KPI “Average Order Value (AOV)” as displayed in Charts of AOV by Product Categories.*
The product category with the highest AOV was Books, with an AOV of **$70**.