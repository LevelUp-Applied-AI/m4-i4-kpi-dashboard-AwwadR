**Executive Summary of Amman Digital Market Analytics**

**Primary Findings:**

1. Through data cleansing, the overall revenue for the digital advertising market in Amman was **JOD 48,701.50** and the total number of orders was **443**. This means the average order value was **JOD 109.94**.
2. Amman was the highest revenue-generating city in the dataset.
3. verage order value was different across product categories and Books had the highest average order value at about 70 JOD.
4. Both total revenue and total number of orders for each month were relatively stable during most of the data period with notable jumps occurring in both metrics in the final month exhibited in the visual displays.
5. The results did not indicate any statistical relationship between customer city and product category.

**Additional Supportive Data:**

Before writing the main analysis, I used test_db.py to explore the data first. I checked the table sizes, order status distribution, suspicious quantities above 100, city values, and product categories. This helped me understand the dataset better before choosing the KPIs.

* Finding 1 is supported by the output from analysis.py *
Total Revenue = **JOD 48,701.50**
Valid Orders = **443**
Average Order Value = **JOD 109.94**

* Finding 2 is supported by the chart revenue_by_city.png *
The City of Amman exhibited as the highest revenue-producing City in the dataset.

* Finding 3 is supported by avg_order_value_by_category.png *
The product category with the highest AOV was Books, with an AOV of **JOD 70**.


**Recommendations**

1. The business should give more attention to high value categories, especially Books and Electronics, because they showed stronger order values than other categories.

2. The business should continue focusing on Amman because it generated the highest total revenue in the dataset.

3. The business should track monthly revenue and monthly order volume together each month to understand whether changes come from order count or order value.